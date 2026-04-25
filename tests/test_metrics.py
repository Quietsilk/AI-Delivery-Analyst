"""Tests for server.metrics — pure metric calculations, no period dependency."""

import sys
import os
import unittest
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from server.metrics import calculate_metrics, _parse_dt, STARTED, DONE


def make_issue(key="T-1", status="Done", created="2024-01-01T00:00:00Z",
               resolutiondate=None, transitions=None):
    histories = []
    for t in (transitions or []):
        histories.append({
            "created": t["date"],
            "items": [{"field": "status", "fromString": t["from"], "toString": t["to"]}],
        })
    return {
        "key": key,
        "fields": {
            "status": {"name": status},
            "created": created,
            "resolutiondate": resolutiondate,
        },
        "changelog": {"histories": histories},
    }


class TestMetricsEmpty(unittest.TestCase):
    def test_empty_returns_zeros(self):
        m = calculate_metrics([])
        self.assertEqual(m["throughput"], 0)
        self.assertEqual(m["cycleTimeDays"], 0)
        self.assertEqual(m["timeToMarketDays"], 0)
        self.assertEqual(m["flowEfficiencyPercent"], 0)
        self.assertEqual(m["backlogSize"], 0)
        self.assertEqual(m["inProgressCount"], 0)
        self.assertEqual(m["reopenedCount"], 0)

    def test_no_period_in_signature(self):
        import inspect
        sig = inspect.signature(calculate_metrics)
        self.assertNotIn("cutoff", sig.parameters)
        self.assertNotIn("period", sig.parameters)


class TestMetricsBasic(unittest.TestCase):
    def test_single_completed_issue(self):
        issue = make_issue(
            status="Done",
            created="2024-01-01T00:00:00Z",
            resolutiondate="2024-01-05T00:00:00Z",
            transitions=[
                {"date": "2024-01-02T00:00:00Z", "from": "To Do", "to": "In Progress"},
                {"date": "2024-01-05T00:00:00Z", "from": "In Progress", "to": "Done"},
            ],
        )
        m = calculate_metrics([issue])
        self.assertEqual(m["cycleTimeDays"], 3.0)      # Jan 2 → Jan 5
        self.assertEqual(m["timeToMarketDays"], 4.0)   # Jan 1 → Jan 5
        self.assertEqual(m["throughput"], 0)           # set by ingestion layer
        self.assertEqual(m["reopenedCount"], 0)

    def test_cycle_time_from_last_started(self):
        issue = make_issue(
            status="Done",
            created="2024-01-01T00:00:00Z",
            resolutiondate="2024-01-10T00:00:00Z",
            transitions=[
                {"date": "2024-01-02T00:00:00Z", "from": "To Do",       "to": "In Progress"},
                {"date": "2024-01-04T00:00:00Z", "from": "In Progress", "to": "To Do"},
                {"date": "2024-01-06T00:00:00Z", "from": "To Do",       "to": "In Progress"},
                {"date": "2024-01-10T00:00:00Z", "from": "In Progress", "to": "Done"},
            ],
        )
        m = calculate_metrics([issue])
        self.assertEqual(m["cycleTimeDays"], 4.0)  # Jan 6 → Jan 10, not Jan 2

    def test_wip_count(self):
        issue = make_issue(
            status="In Progress",
            created="2024-01-01T00:00:00Z",
            transitions=[{"date": "2024-01-02T00:00:00Z", "from": "To Do", "to": "In Progress"}],
        )
        m = calculate_metrics([issue])
        self.assertEqual(m["inProgressCount"], 1)
        self.assertEqual(m["throughput"], 0)

    def test_backlog_count(self):
        issue = make_issue(status="To Do", created="2024-01-01T00:00:00Z")
        m = calculate_metrics([issue])
        self.assertEqual(m["backlogSize"], 1)

    def test_reopened_only_among_done(self):
        # WIP with DONE→IN_PROGRESS transition — not counted (not in completed)
        wip = make_issue(
            status="In Progress",
            created="2024-01-01T00:00:00Z",
            transitions=[
                {"date": "2024-01-02T00:00:00Z", "from": "To Do",       "to": "In Progress"},
                {"date": "2024-01-03T00:00:00Z", "from": "In Progress", "to": "Done"},
                {"date": "2024-01-04T00:00:00Z", "from": "Done",        "to": "In Progress"},
            ],
        )
        m = calculate_metrics([wip])
        self.assertEqual(m["reopenedCount"], 0)

    def test_reopened_counted_for_completed(self):
        done = make_issue(
            status="Done",
            created="2024-01-01T00:00:00Z",
            resolutiondate="2024-01-06T00:00:00Z",
            transitions=[
                {"date": "2024-01-02T00:00:00Z", "from": "To Do",       "to": "In Progress"},
                {"date": "2024-01-03T00:00:00Z", "from": "In Progress", "to": "Done"},
                {"date": "2024-01-04T00:00:00Z", "from": "Done",        "to": "In Progress"},
                {"date": "2024-01-06T00:00:00Z", "from": "In Progress", "to": "Done"},
            ],
        )
        m = calculate_metrics([done])
        self.assertEqual(m["reopenedCount"], 1)

    def test_done_without_resolutiondate(self):
        issue = make_issue(
            status="Done",
            created="2024-01-01T00:00:00Z",
            resolutiondate=None,
            transitions=[
                {"date": "2024-01-02T00:00:00Z", "from": "To Do",       "to": "In Progress"},
                {"date": "2024-01-05T00:00:00Z", "from": "In Progress", "to": "Done"},
            ],
        )
        m = calculate_metrics([issue])
        # Should be counted as completed via last_done transition date
        self.assertEqual(m["cycleTimeDays"], 3.0)


class TestFlowEfficiency(unittest.TestCase):
    def test_basic_50_percent(self):
        issue = make_issue(
            status="Done",
            created="2024-01-01T00:00:00Z",
            resolutiondate="2024-01-07T00:00:00Z",
            transitions=[
                {"date": "2024-01-04T00:00:00Z", "from": "To Do",       "to": "In Progress"},
                {"date": "2024-01-07T00:00:00Z", "from": "In Progress", "to": "Done"},
            ],
        )
        m = calculate_metrics([issue])
        self.assertEqual(m["flowEfficiencyPercent"], 50.0)

    def test_zero_when_no_completed(self):
        m = calculate_metrics([])
        self.assertEqual(m["flowEfficiencyPercent"], 0)

    def test_capped_at_100(self):
        # Anomalous data: created after started → cycle > lead
        issue = make_issue(
            status="Done",
            created="2024-01-05T00:00:00Z",
            resolutiondate="2024-01-07T00:00:00Z",
            transitions=[
                {"date": "2024-01-03T00:00:00Z", "from": "To Do",       "to": "In Progress"},
                {"date": "2024-01-07T00:00:00Z", "from": "In Progress", "to": "Done"},
            ],
        )
        m = calculate_metrics([issue])
        self.assertLessEqual(m["flowEfficiencyPercent"], 100.0)


class TestParseDt(unittest.TestCase):
    def test_z_suffix(self):
        dt = _parse_dt("2024-03-15T10:00:00Z")
        self.assertEqual(dt.tzinfo, timezone.utc)

    def test_plus_offset(self):
        dt = _parse_dt("2024-03-15T10:00:00+00:00")
        self.assertEqual(dt.tzinfo, timezone.utc)

    def test_hhmm_without_colon(self):
        dt = _parse_dt("2024-03-15T12:00:00+0400")
        self.assertEqual(dt.hour, 12)


if __name__ == "__main__":
    unittest.main(verbosity=2)

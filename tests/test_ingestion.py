"""Tests for server.ingestion — pipeline and throughput delta logic."""

import sys
import os
import json
import unittest
import tempfile
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from server.ingestion import run_ingestion, _count_resolved_since
from server.storage import init_db, get_latest, save_snapshot


def tmp_db():
    f = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    f.close()
    init_db(f.name)
    return f.name


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


DONE_ISSUE = make_issue(
    status="Done",
    created="2024-01-01T00:00:00Z",
    resolutiondate="2024-01-05T12:00:00Z",
    transitions=[
        {"date": "2024-01-02T00:00:00Z", "from": "To Do", "to": "In Progress"},
        {"date": "2024-01-05T12:00:00Z", "from": "In Progress", "to": "Done"},
    ],
)


class TestCountResolvedSince(unittest.TestCase):
    def test_no_previous_returns_zero(self):
        self.assertEqual(_count_resolved_since([DONE_ISSUE], None), 0)

    def test_resolved_after_cutoff_is_counted(self):
        # resolved 2024-01-05, cutoff 2024-01-04
        count = _count_resolved_since([DONE_ISSUE], "2024-01-04T00:00:00+00:00")
        self.assertEqual(count, 1)

    def test_resolved_before_cutoff_not_counted(self):
        # resolved 2024-01-05, cutoff 2024-01-10
        count = _count_resolved_since([DONE_ISSUE], "2024-01-10T00:00:00+00:00")
        self.assertEqual(count, 0)

    def test_no_resolutiondate_falls_back_to_changelog(self):
        issue = make_issue(
            status="Done",
            created="2024-01-01T00:00:00Z",
            resolutiondate=None,
            transitions=[
                {"date": "2024-01-06T00:00:00Z", "from": "In Progress", "to": "Done"},
            ],
        )
        count = _count_resolved_since([issue], "2024-01-05T00:00:00+00:00")
        self.assertEqual(count, 1)


class TestRunIngestion(unittest.TestCase):
    def setUp(self):
        self.db = tmp_db()

    def tearDown(self):
        os.unlink(self.db)

    def _mock_fetch(self, issues):
        return patch("server.ingestion.fetch_jira", return_value=issues)

    def test_first_snapshot_throughput_zero(self):
        with self._mock_fetch([DONE_ISSUE]):
            m = run_ingestion("PROJ", "https://j.test", "u", "t", "project=X", self.db)
        self.assertEqual(m["throughput"], 0)

    def test_second_snapshot_throughput_is_delta(self):
        # Manually save a snapshot before DONE_ISSUE resolution (2024-01-05)
        import sqlite3
        con = sqlite3.connect(self.db)
        con.execute(
            "INSERT INTO snapshots (project_key, timestamp, metrics_json) VALUES (?, ?, ?)",
            ("PROJ", "2024-01-03T00:00:00+00:00", '{"throughput": 0}'),
        )
        con.commit()
        con.close()

        # Second run — DONE_ISSUE resolved 2024-01-05 > prev 2024-01-03 → counted
        with self._mock_fetch([DONE_ISSUE]):
            m = run_ingestion("PROJ", "https://j.test", "u", "t", "project=X", self.db)
        self.assertEqual(m["throughput"], 1)

    def test_snapshot_is_saved(self):
        with self._mock_fetch([DONE_ISSUE]):
            run_ingestion("PROJ", "https://j.test", "u", "t", "project=X", self.db)
        result = get_latest("PROJ", self.db)
        self.assertIsNotNone(result)
        self.assertIn("cycleTimeDays", result["metrics"])

    def test_metrics_contain_required_keys(self):
        with self._mock_fetch([DONE_ISSUE]):
            m = run_ingestion("PROJ", "https://j.test", "u", "t", "project=X", self.db)
        for key in ("cycleTimeDays", "timeToMarketDays", "flowEfficiencyPercent",
                    "throughput", "backlogSize", "inProgressCount", "reopenedCount"):
            self.assertIn(key, m)


if __name__ == "__main__":
    unittest.main(verbosity=2)

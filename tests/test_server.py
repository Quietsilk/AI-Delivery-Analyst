"""Regression tests for server.py — AI Delivery Analyst (Python stack).

Covers:
  - calculate_metrics: empty, completed, in-progress, backlog, cutoff, reopened
  - _split_telegram: no split, newline cut, space cut, hard cut
  - _parse_dt: ISO with Z and +00:00
  - fetch_jira: pagination loop (mocked)
  - _handle: full pipeline (mocked Jira + no OpenAI + no Telegram)
  - HTTP GET /  and POST /webhook/sync-report (integration via HTTPServer in a thread)
"""

import json
import sys
import os
import unittest
import threading
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import server


# ── helpers ────────────────────────────────────────────────────────────────────

def make_issue(key="T-1", status="Done", created="2024-01-01T00:00:00Z",
               resolutiondate=None, transitions=None):
    """Build a minimal Jira issue dict with optional changelog transitions."""
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


# ── _parse_dt ──────────────────────────────────────────────────────────────────

class TestParseDt(unittest.TestCase):
    def test_z_suffix(self):
        dt = server._parse_dt("2024-03-15T10:00:00Z")
        self.assertEqual(dt.tzinfo, timezone.utc)
        self.assertEqual(dt.day, 15)

    def test_plus_offset(self):
        dt = server._parse_dt("2024-03-15T10:00:00+00:00")
        self.assertEqual(dt.tzinfo, timezone.utc)

    def test_positive_offset(self):
        dt = server._parse_dt("2024-03-15T12:00:00+04:00")
        self.assertEqual(dt.hour, 12)


# ── calculate_metrics ──────────────────────────────────────────────────────────

class TestCalculateMetrics(unittest.TestCase):
    def test_empty(self):
        m = server.calculate_metrics([])
        self.assertEqual(m["throughput"], 0)
        self.assertEqual(m["cycleTimeDays"], 0)
        self.assertEqual(m["leadTimeDays"], 0)
        self.assertEqual(m["backlogSize"], 0)
        self.assertEqual(m["inProgressCount"], 0)
        self.assertEqual(m["reopenedCount"], 0)

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
        m = server.calculate_metrics([issue])
        self.assertEqual(m["throughput"], 1)
        self.assertEqual(m["cycleTimeDays"], 3.0)   # Jan 2 → Jan 5
        self.assertEqual(m["leadTimeDays"], 4.0)    # Jan 1 → Jan 5
        self.assertEqual(m["reopenedCount"], 0)

    def test_in_progress_issue(self):
        issue = make_issue(
            status="In Progress",
            created="2024-01-01T00:00:00Z",
            transitions=[
                {"date": "2024-01-02T00:00:00Z", "from": "To Do", "to": "In Progress"},
            ],
        )
        m = server.calculate_metrics([issue])
        self.assertEqual(m["inProgressCount"], 1)
        self.assertEqual(m["backlogSize"], 0)
        self.assertEqual(m["throughput"], 0)

    def test_backlog_issue(self):
        issue = make_issue(status="To Do", created="2024-01-01T00:00:00Z")
        m = server.calculate_metrics([issue])
        self.assertEqual(m["backlogSize"], 1)
        self.assertEqual(m["inProgressCount"], 0)
        self.assertEqual(m["throughput"], 0)

    def test_reopened_counted_only_for_completed(self):
        # In Progress issue that was reopened — NOT counted (BUG-3 fix)
        wip = make_issue(
            status="In Progress",
            created="2024-01-01T00:00:00Z",
            transitions=[
                {"date": "2024-01-02T00:00:00Z", "from": "To Do",       "to": "In Progress"},
                {"date": "2024-01-03T00:00:00Z", "from": "In Progress", "to": "Done"},
                {"date": "2024-01-04T00:00:00Z", "from": "Done",        "to": "In Progress"},
            ],
        )
        m = server.calculate_metrics([wip])
        self.assertEqual(m["reopenedCount"], 0)   # not in completed → not counted

    def test_reopened_counted_for_completed_in_period(self):
        # Done issue that was reopened — IS counted
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
        m = server.calculate_metrics([done])
        self.assertEqual(m["reopenedCount"], 1)

    def test_cutoff_filters_old_completed(self):
        old_issue = make_issue(
            status="Done",
            created="2023-12-01T00:00:00Z",
            resolutiondate="2023-12-10T00:00:00Z",
            transitions=[
                {"date": "2023-12-05T00:00:00Z", "from": "To Do", "to": "In Progress"},
                {"date": "2023-12-10T00:00:00Z", "from": "In Progress", "to": "Done"},
            ],
        )
        cutoff = datetime(2024, 1, 1, tzinfo=timezone.utc)
        m = server.calculate_metrics([old_issue], cutoff=cutoff)
        self.assertEqual(m["throughput"], 0)

    def test_cutoff_keeps_recent_completed(self):
        issue = make_issue(
            status="Done",
            created="2024-01-01T00:00:00Z",
            resolutiondate="2024-01-10T00:00:00Z",
            transitions=[
                {"date": "2024-01-05T00:00:00Z", "from": "To Do", "to": "In Progress"},
                {"date": "2024-01-10T00:00:00Z", "from": "In Progress", "to": "Done"},
            ],
        )
        cutoff = datetime(2024, 1, 1, tzinfo=timezone.utc)
        m = server.calculate_metrics([issue], cutoff=cutoff)
        self.assertEqual(m["throughput"], 1)

    def test_mixed_issues(self):
        done = make_issue(
            key="T-1", status="Done",
            created="2024-01-01T00:00:00Z",
            resolutiondate="2024-01-05T00:00:00Z",
            transitions=[
                {"date": "2024-01-02T00:00:00Z", "from": "To Do", "to": "In Progress"},
                {"date": "2024-01-05T00:00:00Z", "from": "In Progress", "to": "Done"},
            ],
        )
        wip = make_issue(
            key="T-2", status="In Progress",
            created="2024-01-03T00:00:00Z",
            transitions=[
                {"date": "2024-01-04T00:00:00Z", "from": "To Do", "to": "In Progress"},
            ],
        )
        backlog = make_issue(key="T-3", status="To Do", created="2024-01-06T00:00:00Z")
        m = server.calculate_metrics([done, wip, backlog])
        self.assertEqual(m["throughput"], 1)
        self.assertEqual(m["inProgressCount"], 1)
        self.assertEqual(m["backlogSize"], 1)

    def test_throughput_all_done(self):
        issues = [
            make_issue(
                key=f"T-{i}", status="Done",
                created="2024-01-01T00:00:00Z",
                resolutiondate="2024-01-05T00:00:00Z",
                transitions=[
                    {"date": "2024-01-02T00:00:00Z", "from": "To Do", "to": "In Progress"},
                    {"date": "2024-01-05T00:00:00Z", "from": "In Progress", "to": "Done"},
                ],
            )
            for i in range(5)
        ]
        m = server.calculate_metrics(issues)
        self.assertEqual(m["throughput"], 5)
        self.assertNotIn("doneRatePercent", m)

    def test_issue_without_started_transition_has_zero_cycle_time(self):
        issue = make_issue(
            status="Done",
            created="2024-01-01T00:00:00Z",
            resolutiondate="2024-01-05T00:00:00Z",
            transitions=[
                {"date": "2024-01-05T00:00:00Z", "from": "To Do", "to": "Done"},
            ],
        )
        m = server.calculate_metrics([issue])
        self.assertEqual(m["cycleTimeDays"], 0)   # no started_at → excluded from avg
        self.assertEqual(m["leadTimeDays"], 4.0)

    def test_resolved_statuses_are_done_like(self):
        for status in ("Closed", "Resolved"):
            issue = make_issue(
                status=status,
                created="2024-01-01T00:00:00Z",
                resolutiondate="2024-01-03T00:00:00Z",
                transitions=[
                    {"date": "2024-01-02T00:00:00Z", "from": "To Do", "to": "In Progress"},
                    {"date": "2024-01-03T00:00:00Z", "from": "In Progress", "to": status},
                ],
            )
            m = server.calculate_metrics([issue])
            self.assertEqual(m["throughput"], 1, f"Expected Done-like for status={status}")

    # ── BUG-1: Done without resolutiondate counts in throughput ────────────────

    def test_done_without_resolutiondate_counts_in_throughput(self):
        issue = make_issue(
            status="Done",
            created="2024-01-01T00:00:00Z",
            resolutiondate=None,  # no resolutiondate — common Jira config
            transitions=[
                {"date": "2024-01-02T00:00:00Z", "from": "To Do",       "to": "In Progress"},
                {"date": "2024-01-05T00:00:00Z", "from": "In Progress", "to": "Done"},
            ],
        )
        m = server.calculate_metrics([issue])
        self.assertEqual(m["throughput"], 1)
        self.assertEqual(m["cycleTimeDays"], 3.0)

    # ── BUG-2: Cycle Time from last STARTED before done, not first ─────────────

    def test_cycle_time_from_last_started(self):
        # Task: To Do → In Progress → Backlog → In Progress → Done
        # First start: Jan 2, last start: Jan 6, done: Jan 10
        # Correct cycle time: Jan 6 → Jan 10 = 4d (not Jan 2 → Jan 10 = 8d)
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
        m = server.calculate_metrics([issue])
        self.assertEqual(m["cycleTimeDays"], 4.0)


# ── _split_telegram ────────────────────────────────────────────────────────────

class TestSplitTelegram(unittest.TestCase):
    def test_short_text_not_split(self):
        self.assertEqual(server._split_telegram("hello"), ["hello"])

    def test_exact_limit_not_split(self):
        text = "x" * 4096
        self.assertEqual(server._split_telegram(text), [text])

    def test_splits_on_newline(self):
        # Total > 4096 so split is forced; newline at pos 3000 is the cut point
        line_a = "a" * 3000
        line_b = "b" * 2000
        text = line_a + "\n" + line_b
        chunks = server._split_telegram(text, max_len=4096)
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0], line_a)
        self.assertEqual(chunks[1], line_b)

    def test_splits_on_space_when_no_newline(self):
        # Total > 4096, no newline — space at pos 3000 is the fallback cut point
        word_a = "a" * 3000
        word_b = "b" * 2000
        text = word_a + " " + word_b
        chunks = server._split_telegram(text, max_len=4096)
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0], word_a)
        self.assertEqual(chunks[1], word_b)

    def test_hard_cut_when_no_whitespace(self):
        text = "x" * 5000
        chunks = server._split_telegram(text, max_len=4096)
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0], "x" * 4096)
        self.assertEqual(chunks[1], "x" * 904)

    def test_no_empty_chunks(self):
        text = "a" * 4096 + "\n" + "b" * 4096
        chunks = server._split_telegram(text, max_len=4096)
        for chunk in chunks:
            self.assertGreater(len(chunk), 0)

    def test_three_chunks(self):
        text = ("word " * 1000).strip()  # ~5000 chars
        chunks = server._split_telegram(text, max_len=2000)
        reconstructed = " ".join(chunks)
        self.assertEqual(reconstructed.replace("  ", " "), text)


# ── fetch_jira pagination ──────────────────────────────────────────────────────

class TestFetchJiraPagination(unittest.TestCase):
    def _make_page(self, keys, is_last, next_page_token=None):
        page = {
            "issues": [
                {"key": k, "fields": {"status": {"name": "To Do"}, "created": "2024-01-01T00:00:00+00:00", "resolutiondate": None}}
                for k in keys
            ],
            "isLast": is_last,
        }
        if next_page_token:
            page["nextPageToken"] = next_page_token
        return page

    def test_single_page(self):
        page = self._make_page(["T-1", "T-2"], is_last=True)
        with patch("server.jira_request", return_value=page):
            result = server.fetch_jira("https://jira.test", "user@test.com", "token", "project = TEST")
        self.assertEqual(len(result["issues"]), 2)

    def test_two_pages(self):
        # cursor-based pagination: page1 returns nextPageToken, page2 is last
        page1 = self._make_page([f"T-{i}" for i in range(50)], is_last=False, next_page_token="cursor-abc")
        page2 = self._make_page([f"T-{i}" for i in range(50, 60)], is_last=True)

        def side_effect(url, auth, body=None):
            if body and body.get("nextPageToken"):
                return page2
            return page1

        with patch("server.jira_request", side_effect=side_effect):
            result = server.fetch_jira("https://jira.test", "user@test.com", "token", "project = TEST")
        self.assertEqual(len(result["issues"]), 60)

    def test_stops_when_page_smaller_than_page_size(self):
        # isLast=False but len(page) < PAGE_SIZE → stop without nextPageToken
        page = self._make_page(["T-1", "T-2"], is_last=False)
        with patch("server.jira_request", return_value=page):
            result = server.fetch_jira("https://jira.test", "user@test.com", "token", "project = TEST")
        self.assertEqual(len(result["issues"]), 2)


# ── HTTP integration ───────────────────────────────────────────────────────────

class TestHttpIntegration(unittest.TestCase):
    """Start the real HTTPServer in a thread and fire real HTTP requests."""

    @classmethod
    def setUpClass(cls):
        import http.server as hs
        cls.server = hs.HTTPServer(("127.0.0.1", 0), server.Handler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def _url(self, path=""):
        return f"http://127.0.0.1:{self.port}{path}"

    def test_get_root_returns_html(self):
        html_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ai-delivery-analyst-dashboard.html")
        if not os.path.exists(html_path):
            self.skipTest("Dashboard HTML not present")
        with urllib.request.urlopen(self._url("/")) as r:
            self.assertEqual(r.status, 200)
            self.assertIn("text/html", r.headers["Content-Type"])

    def test_get_unknown_path_returns_404(self):
        try:
            urllib.request.urlopen(self._url("/nonexistent"))
            self.fail("Expected 404")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 404)

    def test_post_wrong_path_returns_404(self):
        req = urllib.request.Request(
            self._url("/wrong"),
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(req)
            self.fail("Expected 404")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 404)

    def test_post_sync_report_with_mocked_jira(self):
        mock_issues = [
            make_issue(
                key="T-1", status="Done",
                created="2024-01-01T00:00:00Z",
                resolutiondate="2024-01-05T00:00:00Z",
                transitions=[
                    {"date": "2024-01-02T00:00:00Z", "from": "To Do", "to": "In Progress"},
                    {"date": "2024-01-05T00:00:00Z", "from": "In Progress", "to": "Done"},
                ],
            )
        ]
        mock_jira_response = {"issues": mock_issues}

        with patch("server.fetch_jira", return_value=mock_jira_response), \
             patch.dict(os.environ, {"OPENAI_API_KEY": "", "TELEGRAM_BOT_TOKEN": "", "TELEGRAM_CHAT_ID": ""}):
            payload = json.dumps({
                "baseUrl": "https://jira.test",
                "email": "user@test.com",
                "apiToken": "token",
                "jql": "project = TEST",
                "period": "all",
            }).encode()
            req = urllib.request.Request(
                self._url("/webhook/sync-report"),
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req) as r:
                body = json.loads(r.read())

        self.assertTrue(body["ok"])
        self.assertEqual(body["dashboard"]["throughput"], 1)
        self.assertNotIn("doneRatePercent", body["dashboard"])
        self.assertFalse(body["dashboard"]["aiEnabled"])

    def test_post_returns_500_on_jira_error(self):
        with patch("server.fetch_jira", side_effect=Exception("Jira down")):
            payload = json.dumps({
                "baseUrl": "https://jira.test",
                "email": "u", "apiToken": "t", "jql": "project = X",
            }).encode()
            req = urllib.request.Request(
                self._url("/webhook/sync-report"),
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                urllib.request.urlopen(req)
                self.fail("Expected 500")
            except urllib.error.HTTPError as e:
                self.assertEqual(e.code, 500)
                body = json.loads(e.read())
                self.assertFalse(body["ok"])
                self.assertIn("Jira down", body["error"])

    def test_options_cors(self):
        req = urllib.request.Request(
            self._url("/webhook/sync-report"),
            method="OPTIONS",
        )
        with urllib.request.urlopen(req) as r:
            self.assertEqual(r.status, 200)
            self.assertEqual(r.headers["Access-Control-Allow-Origin"], "*")

    def test_period_7d_filters_old_issues(self):
        old_issue = make_issue(
            key="OLD-1", status="Done",
            created="2020-01-01T00:00:00Z",
            resolutiondate="2020-01-05T00:00:00Z",
            transitions=[
                {"date": "2020-01-02T00:00:00Z", "from": "To Do", "to": "In Progress"},
                {"date": "2020-01-05T00:00:00Z", "from": "In Progress", "to": "Done"},
            ],
        )
        with patch("server.fetch_jira", return_value={"issues": [old_issue]}), \
             patch.dict(os.environ, {"OPENAI_API_KEY": "", "TELEGRAM_BOT_TOKEN": "", "TELEGRAM_CHAT_ID": ""}):
            payload = json.dumps({
                "baseUrl": "https://jira.test",
                "email": "u", "apiToken": "t", "jql": "project = X",
                "period": "7d",
            }).encode()
            req = urllib.request.Request(
                self._url("/webhook/sync-report"),
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req) as r:
                body = json.loads(r.read())
        self.assertEqual(body["dashboard"]["throughput"], 0)

    def test_response_includes_throughput_period_label(self):
        mock_issues = [
            make_issue(
                key="T-1", status="Done",
                created="2024-01-01T00:00:00Z",
                resolutiondate="2024-01-05T00:00:00Z",
                transitions=[
                    {"date": "2024-01-02T00:00:00Z", "from": "To Do", "to": "In Progress"},
                    {"date": "2024-01-05T00:00:00Z", "from": "In Progress", "to": "Done"},
                ],
            )
        ]
        with patch("server.fetch_jira", return_value={"issues": mock_issues}), \
             patch.dict(os.environ, {"OPENAI_API_KEY": "", "TELEGRAM_BOT_TOKEN": "", "TELEGRAM_CHAT_ID": ""}):
            payload = json.dumps({
                "baseUrl": "https://jira.test",
                "email": "u", "apiToken": "t", "jql": "project = X",
                "period": "30d",
            }).encode()
            req = urllib.request.Request(
                self._url("/webhook/sync-report"),
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req) as r:
                body = json.loads(r.read())
        self.assertEqual(body["dashboard"]["throughputPeriodLabel"], "30d")
        self.assertIn("reopenedCount", body["dashboard"])


# ── call_openai ───────────────────────────────────────────────────────────────

class TestCallOpenai(unittest.TestCase):
    METRICS = {
        "cycleTimeDays": 3.0, "leadTimeDays": 4.0, "throughput": 5,
        "backlogSize": 2, "inProgressCount": 1, "reopenedCount": 0,
    }

    def _mock_response(self, payload, status=200):
        resp = MagicMock()
        resp.status = status
        resp.read.return_value = json.dumps(payload).encode()
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    def test_returns_output_text(self):
        resp = self._mock_response({"output_text": "Risks: X\nActions: Y"})
        with patch("urllib.request.urlopen", return_value=resp):
            result = server.call_openai(self.METRICS, "sk-test")
        self.assertEqual(result, "Risks: X\nActions: Y")

    def test_fallback_to_choices(self):
        payload = {"choices": [{"message": {"content": "Fallback analysis"}}]}
        resp = self._mock_response(payload)
        with patch("urllib.request.urlopen", return_value=resp):
            result = server.call_openai(self.METRICS, "sk-test")
        self.assertEqual(result, "Fallback analysis")

    def test_fallback_to_default_when_empty(self):
        resp = self._mock_response({})
        with patch("urllib.request.urlopen", return_value=resp):
            result = server.call_openai(self.METRICS, "sk-test")
        self.assertEqual(result, "AI analysis unavailable.")

    def test_retries_on_429_then_succeeds(self):
        err_429 = urllib.error.HTTPError(
            url="", code=429, msg="Too Many Requests",
            hdrs=MagicMock(**{"get.return_value": "1"}), fp=None,
        )
        err_429.read = lambda: json.dumps({}).encode()
        err_429.headers = MagicMock(**{"get.return_value": "1"})
        ok_resp = self._mock_response({"output_text": "OK"})

        call_count = [0]
        def side_effect(*a, **kw):
            call_count[0] += 1
            if call_count[0] < 2:
                raise err_429
            return ok_resp

        with patch("urllib.request.urlopen", side_effect=side_effect), \
             patch("time.sleep"):
            result = server.call_openai(self.METRICS, "sk-test")
        self.assertEqual(result, "OK")
        self.assertEqual(call_count[0], 2)

    def test_raises_on_insufficient_quota(self):
        err_429 = urllib.error.HTTPError(
            url="", code=429, msg="Too Many Requests",
            hdrs=MagicMock(), fp=None,
        )
        err_429.read = lambda: json.dumps({"error": {"code": "insufficient_quota"}}).encode()
        err_429.headers = MagicMock(**{"get.return_value": None})

        with patch("urllib.request.urlopen", side_effect=err_429), \
             patch("time.sleep"):
            with self.assertRaises(RuntimeError) as ctx:
                server.call_openai(self.METRICS, "sk-test")
        self.assertIn("platform.openai.com/settings/billing", str(ctx.exception))

    def test_raises_after_all_retries_exhausted(self):
        err_429 = urllib.error.HTTPError(
            url="", code=429, msg="Too Many Requests",
            hdrs=MagicMock(), fp=None,
        )
        err_429.read = lambda: json.dumps({}).encode()
        err_429.headers = MagicMock(**{"get.return_value": None})

        with patch("urllib.request.urlopen", side_effect=err_429), \
             patch("time.sleep"):
            with self.assertRaises(urllib.error.HTTPError):
                server.call_openai(self.METRICS, "sk-test")

    def test_non_429_error_raises_immediately(self):
        err_500 = urllib.error.HTTPError(
            url="", code=500, msg="Internal Server Error",
            hdrs=MagicMock(), fp=None,
        )
        call_count = [0]
        def side_effect(*a, **kw):
            call_count[0] += 1
            raise err_500

        with patch("urllib.request.urlopen", side_effect=side_effect), \
             patch("time.sleep"):
            with self.assertRaises(urllib.error.HTTPError):
                server.call_openai(self.METRICS, "sk-test")
        self.assertEqual(call_count[0], 1)  # no retry on 500

    def test_prompt_includes_period_label(self):
        captured = []
        ok_resp = self._mock_response({"output_text": "ok"})
        def side_effect(req, timeout=None):
            captured.append(json.loads(req.data.decode())["input"])
            return ok_resp

        with patch("urllib.request.urlopen", side_effect=side_effect):
            server.call_openai(self.METRICS, "sk-test", period_label="last 7 days")
        self.assertIn("last 7 days", captured[0])


# ── send_telegram ──────────────────────────────────────────────────────────────

class TestSendTelegram(unittest.TestCase):
    def _ok_resp(self):
        resp = MagicMock()
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    def test_single_chunk_calls_urlopen_once(self):
        with patch("urllib.request.urlopen", return_value=self._ok_resp()) as mock_open:
            server.send_telegram("hello", "token123", "chat456")
        self.assertEqual(mock_open.call_count, 1)

    def test_multi_chunk_calls_urlopen_multiple_times(self):
        text = ("word " * 1000).strip()  # > 4096 chars → 2 chunks
        with patch("urllib.request.urlopen", return_value=self._ok_resp()) as mock_open:
            server.send_telegram(text, "token", "chat")
        self.assertGreater(mock_open.call_count, 1)

    def test_error_on_first_chunk_stops_sending(self):
        call_count = [0]
        def side_effect(*a, **kw):
            call_count[0] += 1
            raise Exception("network error")

        text = ("word " * 1000).strip()
        with patch("urllib.request.urlopen", side_effect=side_effect):
            server.send_telegram(text, "token", "chat")  # must not raise
        self.assertEqual(call_count[0], 1)  # stopped after first failure

    def test_sends_to_correct_bot_url(self):
        captured = []
        def side_effect(req, timeout=None):
            captured.append(req.full_url)
            return self._ok_resp()

        with patch("urllib.request.urlopen", side_effect=side_effect):
            server.send_telegram("hi", "mytoken", "99")
        self.assertIn("/botmytoken/sendMessage", captured[0])

    def test_payload_contains_chat_id_and_text(self):
        captured = []
        def side_effect(req, timeout=None):
            captured.append(json.loads(req.data.decode()))
            return self._ok_resp()

        with patch("urllib.request.urlopen", side_effect=side_effect):
            server.send_telegram("hello world", "tok", "42")
        self.assertEqual(captured[0]["chat_id"], "42")
        self.assertEqual(captured[0]["text"], "hello world")


# ── calculate_metrics — additional edge cases ──────────────────────────────────

class TestCalculateMetricsEdgeCases(unittest.TestCase):
    def test_average_cycle_time_across_multiple_issues(self):
        issues = [
            make_issue(
                key="T-1", status="Done",
                created="2024-01-01T00:00:00Z",
                resolutiondate="2024-01-03T00:00:00Z",
                transitions=[
                    {"date": "2024-01-01T00:00:00Z", "from": "To Do", "to": "In Progress"},
                    {"date": "2024-01-03T00:00:00Z", "from": "In Progress", "to": "Done"},
                ],
            ),
            make_issue(
                key="T-2", status="Done",
                created="2024-01-01T00:00:00Z",
                resolutiondate="2024-01-05T00:00:00Z",
                transitions=[
                    {"date": "2024-01-01T00:00:00Z", "from": "To Do", "to": "In Progress"},
                    {"date": "2024-01-05T00:00:00Z", "from": "In Progress", "to": "Done"},
                ],
            ),
        ]
        m = server.calculate_metrics(issues)
        self.assertEqual(m["cycleTimeDays"], 3.0)  # avg(2, 4) = 3
        self.assertEqual(m["throughput"], 2)

    def test_negative_cycle_time_excluded_from_average(self):
        # resolved_at < started_at (bad data) → excluded from avg
        issue = make_issue(
            status="Done",
            created="2024-01-01T00:00:00Z",
            resolutiondate="2024-01-02T00:00:00Z",
            transitions=[
                {"date": "2024-01-03T00:00:00Z", "from": "To Do", "to": "In Progress"},
                {"date": "2024-01-02T00:00:00Z", "from": "In Progress", "to": "Done"},
            ],
        )
        m = server.calculate_metrics([issue])
        self.assertEqual(m["cycleTimeDays"], 0)  # negative → excluded → avg of empty = 0

    def test_cutoff_does_not_affect_in_progress(self):
        # Old WIP (started 2023) must still appear in inProgressCount
        old_wip = make_issue(
            status="In Progress",
            created="2023-01-01T00:00:00Z",
            transitions=[
                {"date": "2023-06-01T00:00:00Z", "from": "To Do", "to": "In Progress"},
            ],
        )
        cutoff = datetime(2024, 1, 1, tzinfo=timezone.utc)
        m = server.calculate_metrics([old_wip], cutoff=cutoff)
        self.assertEqual(m["inProgressCount"], 1)
        self.assertEqual(m["throughput"], 0)

    def test_cutoff_does_not_affect_backlog(self):
        old_backlog = make_issue(
            status="To Do",
            created="2023-01-01T00:00:00Z",
        )
        cutoff = datetime(2024, 1, 1, tzinfo=timezone.utc)
        m = server.calculate_metrics([old_backlog], cutoff=cutoff)
        self.assertEqual(m["backlogSize"], 1)


# ── _parse_dt — edge cases ─────────────────────────────────────────────────────

class TestParseDtEdgeCases(unittest.TestCase):
    def test_hhmm_offset_without_colon(self):
        # Python 3.9 fromisoformat doesn't accept +0400, only +04:00
        dt = server._parse_dt("2024-03-15T12:00:00+0400")
        self.assertEqual(dt.hour, 12)

    def test_negative_offset(self):
        dt = server._parse_dt("2024-03-15T08:00:00-05:00")
        self.assertEqual(dt.hour, 8)


# ── _handle — Telegram icon and AI fields ─────────────────────────────────────

class TestHandleTelegramAndAI(unittest.TestCase):
    """Test _handle behaviour for Telegram icon logic and AI fields."""

    @classmethod
    def setUpClass(cls):
        import http.server as hs
        cls.srv = hs.HTTPServer(("127.0.0.1", 0), server.Handler)
        cls.port = cls.srv.server_address[1]
        cls.thread = threading.Thread(target=cls.srv.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def _url(self, path=""):
        return f"http://127.0.0.1:{self.port}{path}"

    def _post(self, payload, env=None):
        env = env or {"OPENAI_API_KEY": "", "TELEGRAM_BOT_TOKEN": "", "TELEGRAM_CHAT_ID": ""}
        with patch("server.fetch_jira", return_value={"issues": payload}), \
             patch.dict(os.environ, env):
            data = json.dumps({
                "baseUrl": "https://jira.test", "email": "u",
                "apiToken": "t", "jql": "project = X", "period": "all",
            }).encode()
            req = urllib.request.Request(
                self._url("/webhook/sync-report"),
                data=data, headers={"Content-Type": "application/json"}, method="POST",
            )
            with urllib.request.urlopen(req) as r:
                return json.loads(r.read())

    def test_ai_enabled_false_when_no_key(self):
        body = self._post([])
        self.assertFalse(body["dashboard"]["aiEnabled"])

    def test_ai_enabled_true_and_analysis_present_when_key_set(self):
        done = make_issue(
            status="Done", created="2024-01-01T00:00:00Z",
            resolutiondate="2024-01-05T00:00:00Z",
            transitions=[
                {"date": "2024-01-02T00:00:00Z", "from": "To Do", "to": "In Progress"},
                {"date": "2024-01-05T00:00:00Z", "from": "In Progress", "to": "Done"},
            ],
        )
        with patch("server.fetch_jira", return_value={"issues": [done]}), \
             patch("server.call_openai", return_value="Summary: good"), \
             patch.dict(os.environ, {"OPENAI_API_KEY": "sk-real", "TELEGRAM_BOT_TOKEN": "", "TELEGRAM_CHAT_ID": ""}):
            data = json.dumps({
                "baseUrl": "https://jira.test", "email": "u",
                "apiToken": "t", "jql": "project = X", "period": "all",
            }).encode()
            req = urllib.request.Request(
                self._url("/webhook/sync-report"),
                data=data, headers={"Content-Type": "application/json"}, method="POST",
            )
            with urllib.request.urlopen(req) as r:
                body = json.loads(r.read())
        self.assertTrue(body["dashboard"]["aiEnabled"])
        self.assertIn("Summary", body["dashboard"]["analysis"])

    def test_ai_error_populated_on_openai_failure(self):
        with patch("server.fetch_jira", return_value={"issues": []}), \
             patch("server.call_openai", side_effect=RuntimeError("quota exceeded")), \
             patch.dict(os.environ, {"OPENAI_API_KEY": "sk-real", "TELEGRAM_BOT_TOKEN": "", "TELEGRAM_CHAT_ID": ""}):
            data = json.dumps({
                "baseUrl": "https://jira.test", "email": "u",
                "apiToken": "t", "jql": "project = X", "period": "all",
            }).encode()
            req = urllib.request.Request(
                self._url("/webhook/sync-report"),
                data=data, headers={"Content-Type": "application/json"}, method="POST",
            )
            with urllib.request.urlopen(req) as r:
                body = json.loads(r.read())
        self.assertTrue(body["ok"])
        self.assertIn("quota exceeded", body["dashboard"]["aiError"])
        self.assertEqual(body["dashboard"]["analysis"], "")

    def test_throughput_period_label_all(self):
        body = self._post([])
        self.assertEqual(body["dashboard"]["throughputPeriodLabel"], "all")

    def test_dashboard_response_shape(self):
        body = self._post([])
        expected_keys = {"cycleTimeDays", "throughput", "throughputPeriodLabel",
                         "leadTimeDays", "reopenedCount", "analysis", "aiEnabled", "aiError"}
        self.assertEqual(set(body["dashboard"].keys()), expected_keys)
        self.assertNotIn("doneRatePercent", body["dashboard"])
        self.assertNotIn("completedCount", body["dashboard"])


# ── load_env ───────────────────────────────────────────────────────────────────

class TestLoadEnv(unittest.TestCase):
    def test_loads_key_value(self):
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".env", delete=False) as f:
            f.write("TEST_QA_KEY=hello_world\n")
            f.write("# comment line\n")
            f.write("EMPTY_LINE=\n")
            name = f.name
        try:
            os.environ.pop("TEST_QA_KEY", None)
            server.load_env(name)
            self.assertEqual(os.environ.get("TEST_QA_KEY"), "hello_world")
        finally:
            os.unlink(name)

    def test_missing_file_is_silent(self):
        server.load_env("/nonexistent/.env")  # must not raise


if __name__ == "__main__":
    unittest.main(verbosity=2)

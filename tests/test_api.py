"""Tests for server.api — HTTP endpoints (no metrics calls)."""

import sys
import os
import json
import sqlite3
import unittest
import tempfile
import threading
import urllib.request
import urllib.error
import http.server
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from server.storage import init_db, save_snapshot
from server import api as api_module


def tmp_db():
    f = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    f.close()
    init_db(f.name)
    return f.name


METRICS = {"cycleTimeDays": 3.0, "timeToMarketDays": 6.0, "throughput": 5,
           "flowEfficiencyPercent": 50.0, "backlogSize": 1, "inProgressCount": 2, "reopenedCount": 0}


class ApiHandler(http.server.BaseHTTPRequestHandler):
    """Minimal handler that wires server.api functions."""
    db_path = None
    jira_credentials = {}

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/latest":
            api_module.handle_get_latest(self, self.__class__.db_path)
        elif path == "/history":
            api_module.handle_get_history(self, self.__class__.db_path)
        else:
            self.send_response(404); self.end_headers()

    def do_POST(self):
        if self.path == "/sync":
            api_module.handle_post_sync(self, self.__class__.db_path, self.__class__.jira_credentials)
        else:
            self.send_response(404); self.end_headers()

    def log_message(self, *a): pass  # silence test output


class TestApiEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = tmp_db()
        save_snapshot("PROJ", METRICS, cls.db)

        ApiHandler.db_path = cls.db
        cls.server = http.server.HTTPServer(("127.0.0.1", 0), ApiHandler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        os.unlink(cls.db)

    def _url(self, path):
        return f"http://127.0.0.1:{self.port}{path}"

    def test_get_latest_returns_snapshot(self):
        with urllib.request.urlopen(self._url("/latest?project=PROJ")) as r:
            body = json.loads(r.read())
        self.assertTrue(body["ok"])
        self.assertEqual(body["snapshot"]["metrics"]["throughput"], 5)

    def test_get_latest_404_for_unknown_project(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(self._url("/latest?project=UNKNOWN"))
        self.assertEqual(ctx.exception.code, 404)

    def test_get_latest_400_without_project_param(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(self._url("/latest"))
        self.assertEqual(ctx.exception.code, 400)

    def test_get_history_returns_list(self):
        with urllib.request.urlopen(self._url("/history?project=PROJ")) as r:
            body = json.loads(r.read())
        self.assertTrue(body["ok"])
        self.assertIsInstance(body["snapshots"], list)
        self.assertEqual(len(body["snapshots"]), 1)

    def test_get_history_with_period(self):
        with urllib.request.urlopen(self._url("/history?project=PROJ&period=30d")) as r:
            body = json.loads(r.read())
        self.assertTrue(body["ok"])
        # Recent snapshot must appear in 30d window
        self.assertEqual(len(body["snapshots"]), 1)

    def test_get_history_400_without_project(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(self._url("/history"))
        self.assertEqual(ctx.exception.code, 400)

    def test_post_sync_returns_202_queued(self):
        payload = json.dumps({
            "project": "PROJ", "baseUrl": "https://j.test",
            "email": "u@t.com", "apiToken": "tok", "jql": "project=PROJ",
        }).encode()
        with patch("server.ingestion.fetch_jira", return_value=[]), \
             patch("server.ingestion.save_snapshot", return_value="2024-01-01T00:00:00+00:00"):
            req = urllib.request.Request(
                self._url("/sync"), data=payload,
                headers={"Content-Type": "application/json"}, method="POST",
            )
            with urllib.request.urlopen(req) as r:
                body = json.loads(r.read())
                self.assertEqual(r.status, 202)
        self.assertTrue(body["ok"])
        self.assertTrue(body["queued"])

    def test_sync_does_not_return_metrics(self):
        payload = json.dumps({
            "project": "PROJ", "baseUrl": "https://j.test",
            "email": "u@t.com", "apiToken": "tok", "jql": "project=PROJ",
        }).encode()
        with patch("server.ingestion.fetch_jira", return_value=[]), \
             patch("server.ingestion.save_snapshot", return_value="2024-01-01T00:00:00+00:00"):
            req = urllib.request.Request(
                self._url("/sync"), data=payload,
                headers={"Content-Type": "application/json"}, method="POST",
            )
            with urllib.request.urlopen(req) as r:
                body = json.loads(r.read())
        self.assertNotIn("metrics", body)
        self.assertNotIn("cycleTimeDays", body)


if __name__ == "__main__":
    unittest.main(verbosity=2)

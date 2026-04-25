"""Tests for server.storage — SQLite snapshot persistence."""

import sys
import os
import json
import unittest
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from server.storage import init_db, save_snapshot, get_latest, get_history, get_previous_snapshot


def tmp_db():
    f = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    f.close()
    return f.name


METRICS_A = {"cycleTimeDays": 3.0, "timeToMarketDays": 6.0, "throughput": 5}
METRICS_B = {"cycleTimeDays": 2.5, "timeToMarketDays": 5.0, "throughput": 8}


class TestInitDb(unittest.TestCase):
    def test_init_creates_table(self):
        db = tmp_db()
        init_db(db)
        import sqlite3
        con = sqlite3.connect(db)
        rows = con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        con.close()
        self.assertIn(("snapshots",), rows)
        os.unlink(db)

    def test_init_idempotent(self):
        db = tmp_db()
        init_db(db)
        init_db(db)   # second call must not raise
        os.unlink(db)


class TestSaveLoad(unittest.TestCase):
    def setUp(self):
        self.db = tmp_db()
        init_db(self.db)

    def tearDown(self):
        os.unlink(self.db)

    def test_save_and_get_latest(self):
        save_snapshot("PROJ", METRICS_A, self.db)
        result = get_latest("PROJ", self.db)
        self.assertIsNotNone(result)
        self.assertEqual(result["metrics"]["cycleTimeDays"], 3.0)
        self.assertIn("timestamp", result)

    def test_latest_returns_most_recent(self):
        save_snapshot("PROJ", METRICS_A, self.db)
        save_snapshot("PROJ", METRICS_B, self.db)
        result = get_latest("PROJ", self.db)
        self.assertEqual(result["metrics"]["throughput"], 8)

    def test_latest_returns_none_for_unknown_project(self):
        result = get_latest("UNKNOWN", self.db)
        self.assertIsNone(result)

    def test_snapshots_are_immutable(self):
        save_snapshot("PROJ", METRICS_A, self.db)
        # Modify METRICS_A — stored snapshot must not change
        METRICS_A["cycleTimeDays"] = 99.0
        result = get_latest("PROJ", self.db)
        self.assertEqual(result["metrics"]["cycleTimeDays"], 3.0)
        METRICS_A["cycleTimeDays"] = 3.0  # restore


class TestGetHistory(unittest.TestCase):
    def setUp(self):
        self.db = tmp_db()
        init_db(self.db)

    def tearDown(self):
        os.unlink(self.db)

    def test_history_oldest_first(self):
        save_snapshot("PROJ", METRICS_A, self.db)
        save_snapshot("PROJ", METRICS_B, self.db)
        history = get_history("PROJ", db_path=self.db)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["metrics"]["throughput"], 5)
        self.assertEqual(history[1]["metrics"]["throughput"], 8)

    def test_history_empty_for_unknown_project(self):
        history = get_history("UNKNOWN", db_path=self.db)
        self.assertEqual(history, [])

    def test_history_filtered_by_period(self):
        # Save one snapshot; period filter should return it (it's recent)
        save_snapshot("PROJ", METRICS_A, self.db)
        history = get_history("PROJ", period="30d", db_path=self.db)
        self.assertEqual(len(history), 1)

    def test_history_period_excludes_no_snapshots_when_all_recent(self):
        save_snapshot("PROJ", METRICS_A, self.db)
        save_snapshot("PROJ", METRICS_B, self.db)
        history = get_history("PROJ", period="7d", db_path=self.db)
        self.assertEqual(len(history), 2)

    def test_history_no_period_returns_all(self):
        for i in range(5):
            save_snapshot("PROJ", {"throughput": i}, self.db)
        history = get_history("PROJ", db_path=self.db)
        self.assertEqual(len(history), 5)


class TestGetPreviousSnapshot(unittest.TestCase):
    def setUp(self):
        self.db = tmp_db()
        init_db(self.db)

    def tearDown(self):
        os.unlink(self.db)

    def test_no_previous_when_only_one_snapshot(self):
        save_snapshot("PROJ", METRICS_A, self.db)
        self.assertIsNone(get_previous_snapshot("PROJ", self.db))

    def test_returns_second_most_recent(self):
        save_snapshot("PROJ", METRICS_A, self.db)
        save_snapshot("PROJ", METRICS_B, self.db)
        prev = get_previous_snapshot("PROJ", self.db)
        self.assertIsNotNone(prev)
        self.assertEqual(prev["metrics"]["throughput"], 5)  # METRICS_A


if __name__ == "__main__":
    unittest.main(verbosity=2)

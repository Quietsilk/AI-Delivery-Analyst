"""SQLite snapshot storage.

Snapshots are immutable — once saved, never modified.
Period filtering happens here (filtering rows by timestamp), not in metrics.
"""

import json
import sqlite3
from datetime import datetime, timezone, timedelta

_DEFAULT_DB = "snapshots.db"


def init_db(db_path=_DEFAULT_DB):
    """Create tables if they don't exist. Safe to call multiple times."""
    con = sqlite3.connect(db_path)
    con.execute("""
        CREATE TABLE IF NOT EXISTS snapshots (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            project_key  TEXT    NOT NULL,
            timestamp    TEXT    NOT NULL,
            metrics_json TEXT    NOT NULL
        )
    """)
    con.commit()
    con.close()


def save_snapshot(project_key, metrics, db_path=_DEFAULT_DB):
    """Persist a metrics snapshot. timestamp = UTC now."""
    ts = datetime.now(timezone.utc).isoformat()
    con = sqlite3.connect(db_path)
    con.execute(
        "INSERT INTO snapshots (project_key, timestamp, metrics_json) VALUES (?, ?, ?)",
        (project_key, ts, json.dumps(metrics)),
    )
    con.commit()
    con.close()
    return ts


def get_latest(project_key, db_path=_DEFAULT_DB):
    """Return the most recent snapshot for a project, or None."""
    con = sqlite3.connect(db_path)
    row = con.execute(
        "SELECT timestamp, metrics_json FROM snapshots WHERE project_key = ? ORDER BY id DESC LIMIT 1",
        (project_key,),
    ).fetchone()
    con.close()
    if not row:
        return None
    return {"timestamp": row[0], "metrics": json.loads(row[1])}


def get_history(project_key, period=None, db_path=_DEFAULT_DB):
    """Return snapshots for a project, optionally filtered by period.

    period: '7d' | '30d' | '90d' | None (all)
    Returns list of {"timestamp": ..., "metrics": {...}} dicts, oldest first.
    """
    _days = {"7d": 7, "30d": 30, "90d": 90}
    cutoff = None
    if period in _days:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=_days[period])).isoformat()

    con = sqlite3.connect(db_path)
    if cutoff:
        rows = con.execute(
            "SELECT timestamp, metrics_json FROM snapshots WHERE project_key = ? AND timestamp >= ? ORDER BY id ASC",
            (project_key, cutoff),
        ).fetchall()
    else:
        rows = con.execute(
            "SELECT timestamp, metrics_json FROM snapshots WHERE project_key = ? ORDER BY id ASC",
            (project_key,),
        ).fetchall()
    con.close()
    return [{"timestamp": r[0], "metrics": json.loads(r[1])} for r in rows]


def get_previous_snapshot(project_key, db_path=_DEFAULT_DB):
    """Return the second-most-recent snapshot (used to compute throughput delta)."""
    con = sqlite3.connect(db_path)
    rows = con.execute(
        "SELECT timestamp, metrics_json FROM snapshots WHERE project_key = ? ORDER BY id DESC LIMIT 2",
        (project_key,),
    ).fetchall()
    con.close()
    if len(rows) < 2:
        return None
    row = rows[1]
    return {"timestamp": row[0], "metrics": json.loads(row[1])}

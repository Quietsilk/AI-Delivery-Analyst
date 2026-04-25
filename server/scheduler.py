"""Background scheduler — runs ingestion on a fixed interval.

Interval is taken from ENV: SYNC_INTERVAL_SECONDS (default: 3600).
Start with: start_scheduler(projects, db_path) — runs in a daemon thread.
"""

import os
import time
import threading


_DEFAULT_INTERVAL = 3600  # 1 hour


def _get_interval():
    try:
        return int(os.environ.get("SYNC_INTERVAL_SECONDS", _DEFAULT_INTERVAL))
    except (ValueError, TypeError):
        return _DEFAULT_INTERVAL


def _run_loop(projects, db_path, interval, stop_event):
    """Core loop: sleep → ingest for each project, repeat."""
    from server.ingestion import run_ingestion
    while not stop_event.is_set():
        stop_event.wait(interval)
        if stop_event.is_set():
            break
        for p in projects:
            try:
                run_ingestion(
                    p["project_key"],
                    p["base_url"],
                    p["email"],
                    p["api_token"],
                    p["jql"],
                    db_path,
                )
            except Exception as e:
                print(f"[scheduler] error for {p['project_key']}: {e}")


def start_scheduler(projects, db_path, interval=None):
    """Start background ingestion loop. Returns (thread, stop_event).

    projects: list of dicts with keys: project_key, base_url, email, api_token, jql
    """
    if interval is None:
        interval = _get_interval()
    stop_event = threading.Event()
    thread = threading.Thread(
        target=_run_loop,
        args=(projects, db_path, interval, stop_event),
        daemon=True,
        name="scheduler",
    )
    thread.start()
    print(f"[scheduler] started — interval {interval}s, {len(projects)} project(s)")
    return thread, stop_event

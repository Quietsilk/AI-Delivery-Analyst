"""HTTP API handler for the new architecture.

Routes:
  GET  /latest?project=KEY          → latest snapshot
  GET  /history?project=KEY&period= → filtered snapshots
  POST /sync                        → trigger ingestion (returns {ok, queued})

Constraint: calculate_metrics is NEVER called here — only storage reads.
"""

import json
import os
import threading
import urllib.parse


def _json_response(handler, code, data):
    body = json.dumps(data).encode()
    handler.send_response(code)
    handler.send_header("Content-Type",   "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin",  "*")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.end_headers()
    handler.wfile.write(body)


def handle_get_latest(handler, db_path):
    """GET /latest?project=KEY"""
    from server.storage import get_latest
    qs  = urllib.parse.parse_qs(urllib.parse.urlparse(handler.path).query)
    key = qs.get("project", [None])[0]
    if not key:
        _json_response(handler, 400, {"ok": False, "error": "project param required"})
        return
    result = get_latest(key, db_path)
    if not result:
        _json_response(handler, 404, {"ok": False, "error": "no snapshots found"})
        return
    _json_response(handler, 200, {"ok": True, "snapshot": result})


def handle_get_history(handler, db_path):
    """GET /history?project=KEY&period=30d"""
    from server.storage import get_history
    qs     = urllib.parse.parse_qs(urllib.parse.urlparse(handler.path).query)
    key    = qs.get("project", [None])[0]
    period = qs.get("period",  [None])[0]
    if not key:
        _json_response(handler, 400, {"ok": False, "error": "project param required"})
        return
    snapshots = get_history(key, period=period, db_path=db_path)
    _json_response(handler, 200, {"ok": True, "snapshots": snapshots})


def handle_post_sync(handler, db_path, jira_credentials):
    """POST /sync — triggers ingestion asynchronously.

    Body (JSON): { project, baseUrl, email, apiToken, jql }
    Returns immediately with { ok: true, queued: true }.
    Does NOT return metrics — caller must poll /latest.
    """
    length = int(handler.headers.get("Content-Length", 0))
    body = json.loads(handler.rfile.read(length)) if length else {}

    project   = body.get("project", "").strip()
    base_url  = body.get("baseUrl",  jira_credentials.get("base_url",  "")).rstrip("/")
    email     = body.get("email",    jira_credentials.get("email",     ""))
    api_token = body.get("apiToken", jira_credentials.get("api_token", ""))
    jql       = body.get("jql",      "").strip()

    if not all([project, base_url, email, api_token, jql]):
        _json_response(handler, 400, {"ok": False, "error": "project, baseUrl, email, apiToken, jql required"})
        return

    def _run():
        from server.ingestion import run_ingestion
        try:
            run_ingestion(project, base_url, email, api_token, jql, db_path)
        except Exception as e:
            print(f"[api] sync error for {project}: {e}")

    threading.Thread(target=_run, daemon=True).start()
    _json_response(handler, 202, {"ok": True, "queued": True})

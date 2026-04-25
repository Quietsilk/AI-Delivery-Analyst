"""Ingestion pipeline: fetch_jira → calculate_metrics → save_snapshot.

Throughput = count of issues resolved between previous and current snapshot.
"""

import json
import base64
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from server.metrics import calculate_metrics, _parse_dt, DONE
from server.storage import save_snapshot, get_latest


PAGE_SIZE = 50


def _jira_request(url, auth, body=None):
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode() if body is not None else None,
        headers={
            "Authorization": f"Basic {auth}",
            "Accept":        "application/json",
            "Content-Type":  "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def fetch_jira(base_url, email, api_token, jql):
    """Fetch all issues + changelogs for the given JQL query."""
    auth = base64.b64encode(f"{email}:{api_token}".encode()).decode()

    all_issues = []
    next_page_token = None
    while True:
        body = {
            "jql": jql, "maxResults": PAGE_SIZE,
            "fieldsByKeys": True,
            "fields": ["summary", "status", "created", "resolutiondate"],
        }
        if next_page_token:
            body["nextPageToken"] = next_page_token
        data = _jira_request(f"{base_url}/rest/api/3/search/jql", auth, body)
        page = data.get("issues", [])
        all_issues.extend(page)
        print(f"  Fetched {len(all_issues)} issues so far")
        next_page_token = data.get("nextPageToken")
        if data.get("isLast", True) or not next_page_token or len(page) < PAGE_SIZE:
            break

    def _fetch_changelog(key):
        try:
            cl = _jira_request(f"{base_url}/rest/api/3/issue/{key}/changelog?maxResults=100", auth)
            return key, cl.get("values", [])
        except Exception:
            return key, []

    print(f"  Fetching changelogs for {len(all_issues)} issues (parallel)…")
    changelogs = {}
    with ThreadPoolExecutor(max_workers=10) as pool:
        for key, values in pool.map(_fetch_changelog, [i["key"] for i in all_issues]):
            changelogs[key] = values

    for issue in all_issues:
        issue["changelog"] = {"histories": changelogs.get(issue["key"], [])}

    return all_issues


def _count_resolved_since(issues, since_ts):
    """Count issues resolved after since_ts (ISO string or None)."""
    if not since_ts:
        return 0
    count = 0
    for issue in issues:
        fields = issue.get("fields") or {}
        # Use resolutiondate or last DONE transition from changelog
        resolved = fields.get("resolutiondate")
        if not resolved:
            histories = issue.get("changelog", {}).get("histories", [])
            transitions = sorted(
                [
                    {"date": h["created"], "to": i.get("toString", "")}
                    for h in histories
                    for i in h.get("items", [])
                    if i.get("field") == "status"
                ],
                key=lambda t: t["date"]
            )
            last_done = next((t for t in reversed(transitions) if t["to"].lower() in DONE), None)
            resolved = last_done["date"] if last_done else None
        if resolved:
            try:
                if _parse_dt(resolved) > _parse_dt(since_ts):
                    count += 1
            except Exception:
                pass
    return count


def run_ingestion(project_key, base_url, email, api_token, jql, db_path="snapshots.db"):
    """Full ingestion pipeline for one project.

    1. Fetch issues from Jira
    2. Calculate metrics (throughput=0 placeholder)
    3. Compute throughput = issues resolved since previous snapshot
    4. Save snapshot to SQLite
    """
    print(f"[ingestion] {project_key}: fetching Jira…")
    issues = fetch_jira(base_url, email, api_token, jql)

    metrics = calculate_metrics(issues)

    # Throughput = delta: resolved since last snapshot timestamp
    prev = get_latest(project_key, db_path)
    since_ts = prev["timestamp"] if prev else None
    metrics["throughput"] = _count_resolved_since(issues, since_ts)

    ts = save_snapshot(project_key, metrics, db_path)
    print(f"[ingestion] {project_key}: snapshot saved at {ts} — {metrics}")
    return metrics

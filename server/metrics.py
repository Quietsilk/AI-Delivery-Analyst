"""Metric calculations — pure functions, no period/cutoff dependency.

All metrics are derived from Jira changelog and computed at ingestion time.
Period filtering is done at the API layer (over stored snapshots), never here.
"""

from datetime import datetime, timezone

STARTED = {"in progress", "selected for development", "в работе", "in development"}
DONE    = {"done", "closed", "resolved", "выполнено", "complete"}


def _parse_dt(s):
    s = s.replace("Z", "+00:00")
    # Python 3.9 fromisoformat requires +HH:MM, not +HHMM
    if len(s) > 5 and s[-5] in ("+", "-") and ":" not in s[-5:]:
        s = s[:-2] + ":" + s[-2:]
    return datetime.fromisoformat(s)


def _avg_days(items, key_a, key_b):
    ds = []
    for item in items:
        if item[key_a] and item[key_b]:
            try:
                da = _parse_dt(item[key_a])
                db = _parse_dt(item[key_b])
                d  = (db - da).total_seconds() / 86400
                if d >= 0:
                    ds.append(d)
            except Exception as e:
                print(f"  [warn] _avg_days: cannot parse {item.get(key_a)!r} / {item.get(key_b)!r} → {e}")
    return round(sum(ds) / len(ds), 1) if ds else 0


def _map_issue(issue):
    """Extract timing fields from a single Jira issue with changelog."""
    histories = issue.get("changelog", {}).get("histories", [])
    transitions = sorted(
        [
            {"date": h["created"], "from": i.get("fromString", ""), "to": i.get("toString", "")}
            for h in histories
            for i in h.get("items", [])
            if i.get("field") == "status"
        ],
        key=lambda t: t["date"]
    )

    last_done = next((t for t in reversed(transitions) if t["to"].lower() in DONE), None)
    started   = next((t for t in reversed(transitions)
                      if t["to"].lower() in STARTED
                      and (not last_done or t["date"] <= last_done["date"])), None)
    status    = (issue.get("fields") or {}).get("status", {}).get("name", "")
    is_done   = status.lower() in DONE
    resolved  = None
    if is_done:
        resolved = (issue.get("fields") or {}).get("resolutiondate") or (last_done["date"] if last_done else None)
    reopened = any(t["from"].lower() in DONE and t["to"].lower() not in DONE for t in transitions)

    return {
        "started_at":  started["date"] if started else None,
        "resolved_at": resolved,
        "created_at":  (issue.get("fields") or {}).get("created"),
        "reopened":    reopened,
    }


def calculate_metrics(issues):
    """Compute delivery metrics from a list of Jira issues with changelogs.

    No period/cutoff — all completed issues are used.
    Throughput is set to 0 here; correct value is computed by ingestion layer
    as the delta between consecutive snapshots.

    Returns a dict with keys:
        cycleTimeDays, timeToMarketDays, flowEfficiencyPercent,
        throughput, backlogSize, inProgressCount, reopenedCount,
        backlogAgingDays
    """
    mapped = [_map_issue(issue) for issue in issues]

    completed   = [i for i in mapped if i["resolved_at"]]
    in_progress = [i for i in mapped if i["started_at"] and not i["resolved_at"]]
    backlog     = [i for i in mapped if not i["started_at"] and not i["resolved_at"]]

    cycle = _avg_days(completed, "started_at", "resolved_at")
    lead  = _avg_days(completed, "created_at",  "resolved_at")
    flow_efficiency = round(min(cycle / lead * 100, 100.0), 1) if lead > 0 else 0

    # Backlog aging: avg days from created_at to now for pure backlog issues
    now = datetime.now(timezone.utc)
    aging_vals = []
    for i in backlog:
        if i["created_at"]:
            try:
                created = _parse_dt(i["created_at"])
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
                aging_vals.append((now - created).total_seconds() / 86400)
            except Exception:
                pass
    backlog_aging = round(sum(aging_vals) / len(aging_vals), 1) if aging_vals else 0

    return {
        "cycleTimeDays":         cycle,
        "timeToMarketDays":      lead,
        "flowEfficiencyPercent": flow_efficiency,
        "throughput":            0,   # set by ingestion layer (delta between snapshots)
        "backlogSize":           len(backlog),
        "inProgressCount":       len(in_progress),
        "reopenedCount":         sum(1 for i in completed if i["reopened"]),
        "backlogAgingDays":      backlog_aging,
    }

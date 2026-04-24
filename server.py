#!/usr/bin/env python3
"""Local webhook server — replaces n8n for the AI Delivery Analyst dashboard.

POST http://localhost:5678/webhook/sync-report
Body: { baseUrl, email, apiToken, jql }
Returns: { ok, dashboard: { predictabilityPercent, cycleTimeDays, throughput, leadTimeDays, analysis } }
"""

import json
import base64
import os
import time
import urllib.request
import urllib.parse
import urllib.error
import http.server
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta

PORT = 5678
PATH = "/webhook/sync-report"

STARTED = {"in progress", "selected for development", "в работе", "in development"}
DONE    = {"done", "closed", "resolved", "выполнено", "complete"}


# ── Metrics ────────────────────────────────────────────────────────────────────

def _parse_dt(s):
    s = s.replace("Z", "+00:00")
    # Python 3.9 fromisoformat requires +HH:MM, not +HHMM
    if len(s) > 5 and s[-5] in ("+", "-") and ":" not in s[-5:]:
        s = s[:-2] + ":" + s[-2:]
    return datetime.fromisoformat(s)


def calculate_metrics(issues, cutoff=None):
    mapped = []
    for issue in issues:
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

        started   = next((t for t in transitions if t["to"].lower() in STARTED), None)
        last_done = next((t for t in reversed(transitions) if t["to"].lower() in DONE), None)
        status    = (issue.get("fields") or {}).get("status", {}).get("name", "")
        is_done   = status.lower() in DONE
        resolved  = None
        if is_done:
            resolved = (issue.get("fields") or {}).get("resolutiondate") or (last_done["date"] if last_done else None)
        reopened = any(t["from"].lower() in DONE and t["to"].lower() not in DONE for t in transitions)

        mapped.append({
            "started_at":  started["date"] if started else None,
            "resolved_at": resolved,
            "created_at":  (issue.get("fields") or {}).get("created"),
            "reopened":    reopened,
        })

    all_completed = [i for i in mapped if i["resolved_at"]]
    in_progress   = [i for i in mapped if i["started_at"] and not i["resolved_at"]]
    backlog       = [i for i in mapped if not i["started_at"] and not i["resolved_at"]]

    # Apply period cutoff only to completed issues
    if cutoff:
        completed = [
            i for i in all_completed
            if _parse_dt(i["resolved_at"]) >= cutoff
        ]
    else:
        completed = all_completed

    def avg_days(items, a, b):
        ds = []
        for item in items:
            if item[a] and item[b]:
                try:
                    da = _parse_dt(item[a])
                    db = _parse_dt(item[b])
                    d  = (db - da).total_seconds() / 86400
                    if d >= 0:
                        ds.append(d)
                except Exception as e:
                    print(f"  [warn] avg_days: cannot parse {item.get(a)!r} / {item.get(b)!r} → {e}")
        return round(sum(ds) / len(ds), 1) if ds else 0

    return {
        "cycleTimeDays":         avg_days(completed, "started_at", "resolved_at"),
        "leadTimeDays":          avg_days(completed, "created_at", "resolved_at"),
        "throughput":            len(completed),
        "predictabilityPercent": round(len(completed) / len(mapped) * 100, 1) if mapped else 0,
        "backlogSize":           len(backlog),
        "inProgressCount":       len(in_progress),
        "completedCount":        len(completed),
        "reopenedCount":         sum(1 for i in mapped if i["reopened"]),
    }


# ── External calls ─────────────────────────────────────────────────────────────

def jira_request(url, auth, body=None):
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


PAGE_SIZE = 50


def fetch_jira(base_url, email, api_token, jql):
    auth = base64.b64encode(f"{email}:{api_token}".encode()).decode()

    # ── Paginate through all issues ───────────────────────────────
    # /search/jql uses cursor pagination (nextPageToken), not offset (startAt)
    # fieldsByKeys:true required to get key + named fields in response
    all_issues     = []
    next_page_token = None
    while True:
        body = {
            "jql": jql, "maxResults": PAGE_SIZE,
            "fieldsByKeys": True,
            "fields": ["summary", "status", "created", "resolutiondate"],
        }
        if next_page_token:
            body["nextPageToken"] = next_page_token
        data = jira_request(f"{base_url}/rest/api/3/search/jql", auth, body)
        page = data.get("issues", [])
        all_issues.extend(page)
        print(f"  Fetched {len(all_issues)} issues so far")
        next_page_token = data.get("nextPageToken")
        if data.get("isLast", True) or not next_page_token or len(page) < PAGE_SIZE:
            break

    # ── Fetch changelog for resolved + actively in-progress issues ─
    # Backlog items (never started) don't need changelog.
    needs_changelog = [
        i["key"] for i in all_issues
        if i.get("fields", {}).get("resolutiondate")
        or i.get("fields", {}).get("status", {}).get("name", "").lower() in STARTED
    ]
    print(f"  Fetching changelogs for {len(needs_changelog)} issues (parallel)…")

    def fetch_changelog(key):
        try:
            cl = jira_request(
                f"{base_url}/rest/api/3/issue/{key}/changelog?maxResults=100",
                auth,
            )
            return key, cl.get("values", [])
        except Exception:
            return key, []

    changelogs = {}
    with ThreadPoolExecutor(max_workers=10) as pool:
        for key, values in pool.map(fetch_changelog, needs_changelog):
            changelogs[key] = values

    for issue in all_issues:
        issue["changelog"] = {"histories": changelogs.get(issue["key"], [])}

    return {"issues": all_issues}


def call_openai(metrics, api_key, period_label="all time"):
    m = metrics
    prompt = (
        f"Delivery metrics ({period_label}):\n"
        f"- Cycle Time: {m['cycleTimeDays']}d\n"
        f"- Lead Time: {m['leadTimeDays']}d\n"
        f"- Throughput: {m['throughput']} issues\n"
        f"- Predictability: {m['predictabilityPercent']}%\n"
        f"- Backlog: {m['backlogSize']} | In Progress: {m['inProgressCount']} | Reopened: {m['reopenedCount']}\n\n"
        "Identify risks, explain causes, suggest 3 specific actions. No generic advice.\n\n"
        "Return:\nSummary: 1-2 sentences\nRisks:\n- ...\nActions:\n- ..."
    )
    body = json.dumps({
        "model":       "o4-mini",
        "reasoning":   {"effort": "medium"},
        "instructions": "You are an expert delivery analyst. Be concise and specific.",
        "input":       prompt,
    }).encode()
    req = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=body,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read())
            return (
                data.get("output_text")
                or (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
                or "AI analysis unavailable."
            )
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 2:
                wait = 5 * (attempt + 1)
                print(f"  OpenAI 429 — retrying in {wait}s (attempt {attempt + 1}/3)…")
                time.sleep(wait)
                continue
            raise


def _split_telegram(text, max_len=4096):
    if len(text) <= max_len:
        return [text]
    chunks, remaining = [], text
    while remaining:
        if len(remaining) <= max_len:
            chunks.append(remaining)
            break
        slice_ = remaining[:max_len]
        cut = slice_.rfind("\n")
        if cut <= 0:
            cut = slice_.rfind(" ")
        if cut <= 0:
            cut = max_len
        chunk = remaining[:cut].rstrip()
        if chunk:
            chunks.append(chunk)
        remaining = remaining[cut:].lstrip()
    return chunks


def send_telegram(text, token, chat_id):
    for chunk in _split_telegram(text):
        body = json.dumps({"chat_id": chat_id, "text": chunk}).encode()
        req  = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        try:
            urllib.request.urlopen(req, timeout=15)
        except Exception as e:
            print(f"Telegram error: {e}")
            break


# ── HTTP handler ───────────────────────────────────────────────────────────────

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ("/", "/index.html"):
            self.send_response(404)
            self.end_headers()
            return
        html_path = os.path.join(os.path.dirname(__file__), "ai-delivery-analyst-dashboard.html")
        with open(html_path, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_POST(self):
        if self.path != PATH:
            self.send_response(404)
            self.end_headers()
            return
        length = int(self.headers.get("Content-Length", 0))
        try:
            body   = json.loads(self.rfile.read(length))
            result = self._handle(body)
            self._json(200, result)
        except Exception as e:
            print(f"Error: {e}")
            self._json(500, {"ok": False, "error": str(e)})

    def _handle(self, body):
        base_url     = body.get("baseUrl", "").rstrip("/")
        email        = body.get("email", "")
        api_token    = body.get("apiToken", "")
        jql          = body.get("jql", "")
        period       = body.get("period", "all")
        project_name = body.get("projectName", "").strip()

        _period_days = {"7d": 7, "30d": 30, "90d": 90}
        cutoff = (
            datetime.now(timezone.utc) - timedelta(days=_period_days[period])
            if period in _period_days else None
        )

        openai_key = os.environ.get("OPENAI_API_KEY", "")
        tg_token   = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        tg_chat    = os.environ.get("TELEGRAM_CHAT_ID", "")

        period_label = period if period == "all" else f"last {_period_days.get(period, '?')} days"
        print(f"Fetching Jira: {base_url} / {jql}  [period: {period_label}]")
        data    = fetch_jira(base_url, email, api_token, jql)
        metrics = calculate_metrics(data.get("issues", []), cutoff)
        print(f"Metrics: {metrics}")

        analysis  = ""
        ai_error  = ""
        if openai_key:
            print("Calling OpenAI…")
            try:
                analysis = call_openai(metrics, api_key=openai_key, period_label=period_label)
            except Exception as e:
                ai_error = str(e)
                print(f"OpenAI error: {e}")

        if tg_token and tg_chat:
            icon    = "🟢" if metrics["predictabilityPercent"] >= 80 else ("🟡" if metrics["predictabilityPercent"] >= 60 else "🔴")
            date    = datetime.now().strftime("%-d %b %Y")
            title   = project_name if project_name else "Delivery Report"
            period_str = {"7d": "7 дней", "30d": "30 дней", "90d": "90 дней"}.get(period, "всё время")
            reopened_line = f"⚠️ Reopened: {metrics['reopenedCount']}\n" if metrics["reopenedCount"] else ""
            tg_text = "\n".join(filter(None, [
                f"📊 {title} — {date}",
                f"Период: {period_str}",
                "",
                "━━━ Метрики ━━━",
                f"✅ Завершено: {metrics['completedCount']}   🔄 В работе: {metrics['inProgressCount']}   📋 Бэклог: {metrics['backlogSize']}",
                f"⚠️ Переоткрыто: {metrics['reopenedCount']}" if metrics["reopenedCount"] else None,
                f"{icon} Предсказуемость: {metrics['predictabilityPercent']}%",
                f"⏱ Cycle Time: {metrics['cycleTimeDays']}д   📅 Lead Time: {metrics['leadTimeDays']}д   🚀 Throughput: {metrics['throughput']}",
                "",
                "━━━ AI-анализ ━━━",
                analysis or "—",
            ]))
            send_telegram(tg_text, tg_token, tg_chat)

        return {
            "ok": True,
            "dashboard": {
                "predictabilityPercent": metrics["predictabilityPercent"],
                "cycleTimeDays":         metrics["cycleTimeDays"],
                "throughput":            metrics["throughput"],
                "leadTimeDays":          metrics["leadTimeDays"],
                "analysis":              analysis,
                "aiEnabled":             bool(openai_key),
                "aiError":               ai_error,
            },
        }

    def _json(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")

    def log_message(self, fmt, *args):
        print(f"  {fmt % args}")


def load_env(path):
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())


if __name__ == "__main__":
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    load_env(env_path)

    server = http.server.HTTPServer(("", PORT), Handler)
    print(f"✓ Server on http://localhost:{PORT}")
    print(f"  Open:    http://localhost:{PORT}")
    print()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")

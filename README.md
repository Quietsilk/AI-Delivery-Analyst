# AI Delivery Analyst

An early-warning system for delivery risks. Connects to Jira, calculates metrics from changelog, analyses them via AI, and sends a report to Telegram — with zero manual effort.

---

## What it does

1. Fetches issues from Jira via JQL query (cursor-based pagination)
2. Loads changelog for every issue in parallel (up to 10 threads)
3. Calculates delivery metrics: Cycle Time, Lead Time, Throughput, Reopened
4. Filters completed issues by period (7d / 30d / 90d / All)
5. Analyses metrics via OpenAI → Summary, Risks, Actions
6. Sends a report to Telegram (smart chunking ≤ 4096 chars)
7. Displays everything in a browser dashboard in real time

---

## Quick start

```bash
# 1. Clone
git clone https://github.com/Quietsilk/AI-Delivery-Analyst
cd AI-Delivery-Analyst

# 2. Configure environment (AI and Telegram are optional)
cp .env.example .env
# Edit .env

# 3. Run
./start.sh
# → http://localhost:5678
```

Jira credentials (URL, email, API token) are entered directly in the dashboard and stored in localStorage.

---

## Built with AI

This project was built end-to-end using Claude (Anthropic) as the primary coding tool.
The development process included iterative spec writing, code generation, bug discovery,
test authoring, and QA — all driven through AI-assisted sessions.
The goal was to demonstrate how a senior engineer can leverage AI coding tools
to ship a production-quality tool faster and with higher test coverage than traditional solo development.

---

## Stack

- **Python 3.9+** — stdlib-only server, no dependencies (`pip install` not required)
- **HTML/CSS/JS** — single-file dashboard, runs in the browser
- **Jira Cloud REST API** — `/rest/api/3/search/jql` + `/rest/api/3/issue/{key}/changelog`
- **OpenAI Responses API** — model `o4-mini`, optional
- **Telegram Bot API** — report delivery, optional

---

## Project structure

```
ai-delivery-analyst/
├── server.py                          # HTTP server: routing, Jira, metrics, OpenAI, Telegram
├── ai-delivery-analyst-dashboard.html # UI (single file)
├── start.sh                           # Launch wrapper
├── tests/
│   └── test_server.py                 # 37 regression tests (stdlib unittest)
├── docs/
│   ├── architecture.md
│   ├── backlog.md
│   └── risks.md
├── .env.example                       # Environment variable template
└── .env                               # Local secrets (not in git)
```

---

## Environment variables

| Variable | Description | Required |
|---|---|---|
| `OPENAI_API_KEY` | OpenAI key for AI analysis | No |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | No |
| `TELEGRAM_CHAT_ID` | Target chat or group ID | No |

Jira credentials are entered in the UI and never stored on the server.

---

## Metrics

All metrics are calculated from Jira changelog — not from static fields.

| Metric | Definition |
|---|---|
| **Cycle Time** | Average time from the last "In Progress" transition to completion |
| **Lead Time** | Average time from issue creation to completion |
| **Throughput** | Number of completed issues in the selected period (shown as "15 / 30d") |
| **Reopened** | Count of completed issues that were previously returned from Done |

Status sets (case-insensitive):

```python
STARTED = {"in progress", "selected for development", "в работе", "in development"}
DONE    = {"done", "closed", "resolved", "выполнено", "complete"}
```

---

## Period filter

The filter applies **only to completed issues** by `resolved_at` date.
In Progress and Backlog always reflect the current state regardless of period.

---

## AI analysis

When `OPENAI_API_KEY` is set, the server calls `o4-mini` and returns:

- **Summary** — 1–2 sentences on delivery health
- **Risks** — specific risks with root causes
- **Actions** — 3 recommended actions

AI states in the dashboard:

| State | Cause | UI shows |
|---|---|---|
| Analysis ready | OpenAI responded | Summary, Risks, Actions |
| `AI unavailable: …` | API error (429, timeout) | Error text in all three panels |
| `AI not configured` | `OPENAI_API_KEY` not set | Hint in panels |

---

## Jira API

The server uses the new `/rest/api/3/search/jql` endpoint (Jira Cloud):

- `fieldsByKeys: true` is required to get `key` and named fields
- Pagination via `nextPageToken` (cursor-based, not offset)
- Changelog is fetched in parallel (up to 10 threads) for all issues

---

## Tests

```bash
python3 -m unittest tests/test_server.py -v
```

37 tests, zero external dependencies. Coverage:

| Group | Tests |
|---|---|
| `calculate_metrics` — empty, completed, WIP, backlog, cutoff, reopened, cycle/lead time, BUG-1/2/3 | 14 |
| `_split_telegram` — short text, newline/space split, hard cut, empty chunks | 7 |
| `fetch_jira` — single page, cursor pagination, stop on small page | 3 |
| HTTP integration — GET, 404, CORS, POST pipeline, 500 on Jira error, period=7d, throughputPeriodLabel | 8 |
| `_parse_dt` — Z, +00:00, +HH:MM formats | 3 |
| `load_env` — file load, missing file | 2 |

---

## Known limitations

- STARTED/DONE statuses are hardcoded in `server.py` (not configurable via UI)
- Sync history is stored only in browser localStorage (up to 30 records)
- Single JQL query per sync (multi-source not implemented)
- No scheduled/cron execution — manual sync only via UI button

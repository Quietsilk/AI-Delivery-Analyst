# AI Delivery Analyst

**Early warning system for delivery — detects risks before they surface in Jira boards or retrospectives.**

---

## Problem

Delivery issues are almost always detected too late.

By the time a Delivery Manager sees rising cycle time, sprint overcommitment, or growing WIP, the sprint is already failing or the release is already at risk.

Jira dashboards provide data, but they require manual interpretation and are inherently reactive.

Delivery Managers do not lack data. They lack early signals that force action before delivery fails.

---

## Solution

AI Delivery Analyst is a fully automated delivery intelligence system.

It runs daily, pulls data directly from Jira, computes delivery metrics using explicit rules, detects risk signals, and delivers a decision-ready report — without dashboards, manual analysis, or interpretation lag.

The system is not a reporting tool. It is a decision-support layer that enables earlier intervention.

---

## Key Capabilities

**Multi-source delivery contexts.** Supports multiple Jira projects simultaneously, each with independent methodology (Kanban / Scrum), JQL scope, and workflow configuration.

**Methodology-aware metrics.** Kanban uses flow-based metrics (WIP, throughput, cycle time, lead time). Scrum uses sprint commitment and predictability derived from Jira Agile API.

**Daily automated reporting.** Runs on schedule (cron or n8n) and delivers a complete delivery snapshot to Telegram or Slack — no manual trigger required.

**Deterministic metrics engine.** All metrics are calculated from Jira changelog data using explicit rules. No approximations, no reliance on custom fields.

**Graceful degradation.** If AI is unavailable, the system still delivers a complete metrics report. No hard dependency on LLM.

**Dry-run mode.** Full pipeline can be executed locally on mock data — including metrics, prompt generation, and reporting — without external APIs.

---

## Architecture

```
Jira Cloud REST API ──► Ingestion
Jira Agile API ─────►  (changelog, sprint data)
                              │
                        Domain Model
                        (Issue entity)
                              │
                       Metrics Engine
                    ┌──────────────────┐
                  kanban             scrum
              flow metrics      sprint commitment
              (WIP, CT, LT,    (committed/completed
               throughput)      via Agile API)
                    └──────────────────┘
                              │
                     Risk Signal Detection
                              │
                     Prompt Builder
                              │
                     OpenAI (interpretation only)
                              │
                     Report Formatter
                              │
                     Telegram / Slack Delivery
```

Each layer has a single responsibility:

- Metrics are deterministic and independent
- Risk signals are generated before AI
- AI interprets but does not calculate
- Delivery layer is decoupled from logic

---

## Metrics Model

Metrics are derived from Jira changelog history, not from static fields.

**Cycle Time** — time from first transition into a started status (e.g. "In Progress") to resolution.

**Lead Time** — time from issue creation to resolution. Indicates queuing and planning efficiency.

**Throughput** — number of completed issues within the analysis window.

**Predictability (Kanban)** — completed / total issues over a rolling window.

**Predictability (Scrum)** — completed committed issues / total committed issues in the active sprint (via Jira Agile API).

**Reopened signal** — detected from changelog transitions from Done → non-Done. Used as a quality indicator.

---

## Risk Detection

Risk signals are generated deterministically before AI analysis.

| Signal | Definition | Implication |
|---|---|---|
| Low predictability | < 70% | Overcommitment or scope instability |
| Cycle time increase | Above baseline | Bottleneck forming |
| High WIP | Relative to throughput | Context switching / blocked flow |
| Reopened issues | Done → active | Quality issues |
| Backlog growth | Increasing backlog | Intake exceeds capacity |
| No active sprint | Scrum board idle | Planning failure |

Risk signals can be used independently of AI. AI does not decide what is a risk — it explains it.

---

## System vs AI Responsibilities

| Responsibility | System | AI |
|---|---|---|
| Fetch Jira data | ✅ | ✗ |
| Compute metrics | ✅ | ✗ |
| Detect risk signals | ✅ | ✗ |
| Identify root causes | ✗ | ✅ |
| Suggest actions | ✗ | ✅ |
| Deliver report | ✅ | ✗ |

AI is an interpretation layer, not a dependency.

---

## Decision Loop

1. System detects deviation (e.g. predictability drop)
2. Risk signal is generated
3. AI explains likely causes
4. Manager takes action (scope, WIP, priorities)

The system closes the gap between signal and decision.

---

## Example Scenario

**Input:** Two Jira projects — one Kanban, one Scrum. Active sprint with 8 committed issues.

**System detects:**
- Scrum predictability: 37.5% at sprint midpoint
- Kanban WIP above safe threshold
- Reopened issues present

**AI analysis:**
- Sprint likely to miss committed scope
- WIP overload slowing delivery
- Quality issues causing rework

**Decision enabled:**
- Descope sprint mid-cycle
- Reduce WIP
- Investigate QA / acceptance gaps

Without the system, this would be detected at sprint end.

---

## Why Not Jira Dashboards

Jira dashboards show metrics.

This system:
- defines metrics explicitly from changelog data
- detects risk signals automatically
- interprets them in context
- delivers a decision-ready report

Jira shows data. This system drives action.

---

## Impact

- Shifts delivery management from reactive to proactive
- Enables mid-sprint intervention instead of end-of-sprint analysis
- Reduces time-to-detect delivery degradation
- Eliminates manual reporting and interpretation
- Provides consistent delivery signals across multiple projects

---

## Technical Highlights

- Changelog-based metric calculation (no custom fields required)
- Scrum predictability via Jira Agile API
- Multi-project configuration via `JIRA_SOURCES`
- OpenAI Responses API used strictly for interpretation
- Telegram delivery with message chunking
- Fully testable pipeline via dry-run mode

---

## How to Run

```bash
cp .env.example .env

# Configure:
# JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN, JIRA_SOURCES
# OPENAI_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

npm install
npm run dev
```

Test without external APIs:

```bash
node --loader ts-node/esm src/scripts/dryRun.ts
```

Multi-project source format:
```
kanban|kanban|KAN|project = "KAN" ORDER BY updated DESC|In Progress;scrum|scrum|SCRUM|project = "SCRUM" ORDER BY updated DESC|In Progress
```

---

## Summary

AI Delivery Analyst is not a reporting tool.

It is a delivery observability and decision-support system that detects risks early and enables faster, better decisions.

# AI Delivery Analyst

**Delivery risk detection and metrics intelligence — automated, daily, without dashboards.**

---

## Problem

Delivery issues are visible in hindsight. By the time a Delivery Manager sees a pattern — rising cycle time, sprint overcommitment, growing WIP — the sprint is already failing or the release is already at risk.

Jira dashboards exist but require manual interpretation. Teams don't lack data. They lack a system that reads that data daily, computes what matters, and tells them what to act on before it's too late.

This project is an answer to that gap.

---

## Solution

A fully automated pipeline that runs daily, reads Jira at the source level, computes delivery metrics per methodology (kanban flow vs. scrum commitment), detects risk signals, and delivers an actionable report — no manual steps, no dashboards, no interpretation lag.

The system separates two concerns deliberately:

- **Metric computation is deterministic.** Cycle time, lead time, throughput, and predictability are calculated from raw Jira changelog data using explicit rules — not estimates, not approximations.
- **AI handles interpretation.** OpenAI receives a structured snapshot and produces risk identification and recommended actions. AI does not touch metric calculation.

---

## Key Capabilities

**Multi-source delivery contexts.** A single run covers multiple Jira projects simultaneously, each with its own methodology, JQL scope, and started-status definition. Kanban and Scrum are processed differently by design — not treated as the same data shape.

**Sprint-aware Scrum predictability.** For Scrum boards, predictability is derived from active sprint commitment (completed committed / total committed) via Jira Agile API — not from raw issue ratios, which produce meaningless numbers mid-sprint.

**Daily delivery snapshot with no manual trigger.** The pipeline is designed to run on a schedule (cron or n8n). Report arrives in Telegram every morning without anyone initiating it.

**Graceful degradation.** If OpenAI is unavailable or over quota, the report still runs and delivers metrics. No hard dependency on AI for core functionality.

**Dry-run mode.** Full pipeline — metrics, prompt construction, report formatting — runs locally on mock data with zero network calls. Useful for development and demonstration.

---

## Architecture

```
Jira Cloud REST API ──► Ingestion
Jira Agile API ─────►  (changelog expand, sprint data)
                              │
                        Domain Model
                        (Issue: id, type, status,
                         createdAt, startedAt,
                         resolvedAt, assignee,
                         storyPoints, reopened)
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
                     (structured snapshot)
                              │
                     OpenAI Responses API
                     (interpretation only)
                              │
                     Report Formatter
                     (metrics + AI insights)
                              │
                     Telegram / Slack Delivery
```

Each layer has a single responsibility. The Metrics Engine has no knowledge of delivery channels. The AI layer receives a read-only snapshot. The Report Formatter does not call any APIs.

---

## Metrics Model

Metrics are derived from Jira changelog history, not from field values.

**Cycle Time** = time from first transition into a started status (e.g., "In Progress") to resolution date. Computed per completed issue, averaged across the scope window.

**Lead Time** = time from issue creation to resolution. Includes waiting time before work started. Higher lead time relative to cycle time indicates queuing or planning inefficiency.

**Throughput** = count of resolved issues within the analysis scope. Used as a flow health indicator for kanban; for scrum it is compared against sprint commitment.

**Predictability (Kanban)** = completed / total issues in scope. A flow-based proxy. Less meaningful mid-sprint; most useful over rolling time windows.

**Predictability (Scrum)** = completed committed issues / total committed issues in active sprint. Pulled from Jira Agile API. Sprint scope is the denominator — not the total project scope. Falls back to kanban-style proxy if no active sprint is detected.

**Reopened flag** = set if any changelog entry transitions an issue *from* Done to any non-done status. Used as a quality signal, not a metric in itself.

---

## Risk Detection

The system passes the following signals to AI for interpretation. These are computed deterministically before AI is involved.

| Signal | Definition | Risk Implication |
|---|---|---|
| Predictability < 70% | Completion rate below threshold | Overcommitment or scope instability |
| Cycle Time increasing | Current CT > rolling baseline | Bottleneck forming in flow |
| High WIP | In-progress count relative to throughput | Context switching, blocked work |
| Reopened issues present | Issues transitioned out of Done | Quality or acceptance criteria issues |
| Backlog growing | Backlog size increasing without throughput increase | Intake exceeds capacity |
| No active sprint (Scrum) | Board has future sprints but none started | Planning lag, sprint not initiated |

AI receives these signals as a structured input and is tasked with identifying root causes and suggesting actions — not with detecting the signals themselves.

---

## System vs AI Responsibilities

| Responsibility | System | AI |
|---|---|---|
| Fetch Jira data | ✅ | ✗ |
| Compute cycle time, lead time | ✅ | ✗ |
| Calculate sprint predictability | ✅ | ✗ |
| Detect risk signals | ✅ | ✗ |
| Identify root causes | ✗ | ✅ |
| Suggest actions | ✗ | ✅ |
| Format and deliver report | ✅ | ✗ |

If OpenAI is unavailable, the system still delivers a complete metrics report. AI is an enhancement layer, not a dependency.

---

## Example Scenario

**Input:** Two Jira projects — one kanban (KAN), one scrum (SCR). Active sprint in SCR with 8 committed issues.

**System computes:**
- KAN: CT = 4.2d, LT = 9.1d, throughput = 6, WIP = 4, predictability = 55%
- SCR: active sprint "Sprint 12", 3/8 committed issues completed, sprint predictability = 37.5%
- SCR: 2 issues reopened this week

**Risk signals detected:**
- SCR predictability 37.5% — well below 70% threshold with sprint half complete
- KAN WIP = 4 against throughput of 6 — elevated
- 2 reopened issues in SCR — quality signal

**AI receives** a structured snapshot with these numbers and signals.

**Report delivered to Telegram:**
```
📊 Delivery Report — 19 Apr 2026

━━━ Overview ━━━
✅ Completed: 9   🔄 In Progress: 6   📋 Backlog: 5
⚠️ Reopened: 2   🔴 Predictability: 46%
⏱ Cycle Time: 4.8d   📅 Lead Time: 9.4d   🚀 Throughput: 9

━━━ AI Analysis ━━━
Summary: SCR sprint is at serious risk of incomplete delivery with 37.5%
predictability at midpoint. KAN flow is under pressure from elevated WIP.

Risks:
- SCR sprint likely to miss 4-5 committed items at current pace
- 2 reopened issues suggest acceptance criteria gaps or QA handoff issues
- KAN WIP-to-throughput ratio indicates parallel work is slowing completion

Actions:
- Review SCR sprint scope now — descope or reassign before end of week
- Block new KAN intake until WIP drops to ≤3
- Run a 15-min retro on reopened items to identify the root cause pattern
```

**Decision enabled:** Sprint descoping conversation happens on day 10, not day 14.

---

## Impact

| Before | After |
|---|---|
| Delivery issues visible at sprint end | Issues surfaced mid-sprint |
| Manual Jira board review | Automated daily snapshot |
| Gut-feel sprint health | Quantified predictability signal |
| Generic retrospective | Targeted action from specific signals |
| One project at a time | Multi-project aggregate + per-source breakdown |

---

## Technical Highlights

- Changelog-based metric derivation — no custom Jira fields required for cycle time
- Scrum predictability uses Jira Agile API board and sprint endpoints, not issue counts
- `JIRA_SOURCES` config supports N projects with independent methodology, JQL, and status mapping
- OpenAI Responses API with `reasoning.effort` — deterministic prompt, AI handles interpretation only
- Telegram delivery with 4096-char chunking for long reports
- Full pipeline testable locally via `dryRun.ts` — no Jira or OpenAI credentials needed

---

## How to Run

```bash
cp .env.example .env
# Configure: JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN, JIRA_SOURCES
# Configure: OPENAI_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

npm install
npm run dev
```

Test without network:
```bash
node --loader ts-node/esm src/scripts/dryRun.ts
```

Multi-project source format:
```
key|methodology|projectKey|jql|startedStatuses
kanban|kanban|KAN|project = "KAN" ORDER BY updated DESC|In Progress;scrum|scrum|SCRUM|project = "SCRUM" ORDER BY updated DESC|In Progress
```

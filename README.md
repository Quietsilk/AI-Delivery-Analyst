# AI Delivery Analyst

> Automated delivery intelligence: pulls real Jira data, calculates engineering metrics, and delivers AI-generated insights to Telegram — without manual work.

Built to demonstrate a systems approach to delivery management: layered architecture, real API integrations, and production-ready automation thinking.

---

## What It Does

Runs daily. No dashboards, no manual reports. Just a message in Telegram with the delivery snapshot your team actually needs.

- Connects to one or multiple Jira projects (kanban and scrum)
- Calculates Cycle Time, Lead Time, Throughput, and Predictability per source and in aggregate
- For scrum boards: enriches predictability with active sprint commitment data via Jira Agile API
- Sends a structured delivery snapshot to OpenAI and gets back actionable insights
- Delivers the full report to Telegram (with graceful fallback if AI is unavailable)

## Why It Exists

Most delivery reporting is manual, delayed, and generic. This system automates the entire pipeline — from raw Jira data to a prioritised, risk-aware report — so a Delivery Manager can focus on acting, not collecting.

---

## Architecture

```
Jira Cloud API ──► Ingestion Layer
                        │
                   Domain Model (Issue)
                        │
                   Metrics Engine
              (Cycle Time · Lead Time · Throughput · Predictability)
                        │
              ┌─────────┴─────────┐
           kanban               scrum
           flow metrics     sprint commitment
                        │
                   AI Analysis (OpenAI Responses API)
                        │
                   Report Formatter
                        │
                   Telegram Delivery
```

**Layers:**

- `src/domain` — Issue entity and metrics calculation
- `src/services/jira` — Jira REST + Agile API client, issue mapping, sprint insights
- `src/services/analysis` — prompt builder and OpenAI Responses API integration
- `src/services/reporting` — report formatter and Telegram/Slack publisher
- `src/workflows` — daily analysis orchestration
- `src/scripts` — dry-run testing, Jira simulation, data inspection

---

## Stack

TypeScript · Node.js 20 · Jira Cloud REST API · Jira Agile API · OpenAI Responses API (o4-mini) · Telegram Bot API

---

## Key Engineering Decisions

**Scrum vs Kanban handled differently by design.** Kanban sources use flow-based metrics (WIP, throughput, lead time). Scrum sources enrich predictability from active sprint commitment via Jira Agile API — not raw issue count.

**Graceful degradation.** If OpenAI is unavailable, the report still runs and delivers to Telegram with metrics intact. No hard failures on optional dependencies.

**Multi-source from day one.** `JIRA_SOURCES` supports multiple projects with independent methodology, JQL, and status configuration — composable delivery contexts out of the box.

**Testable without network.** `dryRun.ts` runs the full pipeline on mock data — metrics, prompt construction, report formatting — no Jira or OpenAI connection needed.

---

## Quick Start

```bash
cp .env.example .env
# fill in JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN, JIRA_SOURCES
# fill in OPENAI_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

npm install
npm run dev
```

Test the full pipeline without network calls:

```bash
node --loader ts-node/esm src/scripts/dryRun.ts
```

---

## Configuration

Multi-project sources via `JIRA_SOURCES`:

```
kanban|kanban|KAN|project = "KAN" ORDER BY updated DESC|In Progress;scrum|scrum|SCRUM|project = "SCRUM" ORDER BY updated DESC|In Progress
```

Format: `key|methodology|projectKey|jql|startedStatuses`

If `JIRA_SOURCES` is not set, falls back to `JIRA_PROJECT_KEY` + `JIRA_JQL`.
If `OPENAI_API_KEY` is not set or quota is exceeded, the report is delivered without AI analysis.

---

## RU — О проекте

Система автоматического delivery-анализа: забирает данные из Jira, считает ключевые метрики разработки и отправляет AI-отчёт в Telegram — без участия человека.

**Для kanban** — метрики потока: WIP, throughput, cycle time, lead time.
**Для scrum** — predictability считается от commitment активного спринта через Jira Agile API.

Проект показывает системное мышление в автоматизации delivery: разделение на слои, работу с реальными API, graceful degradation и production-ready подход к конфигурации и тестированию.

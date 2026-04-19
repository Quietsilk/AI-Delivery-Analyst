# AI Delivery Analyst

Automated delivery analytics: pulls Jira data, calculates engineering metrics, and generates actionable reports via AI.

---

## What It Does

- Fetches issues from one or multiple Jira projects (kanban + scrum)
- Calculates Cycle Time, Lead Time, Throughput, and Predictability per source and in aggregate
- For scrum: enriches metrics with active sprint data via Jira Agile API
- Builds a structured delivery snapshot and sends it to OpenAI Responses API
- Formats and publishes an actionable report

## Stack

TypeScript · Node.js 20 · Jira Cloud REST API · Jira Agile API · OpenAI Responses API (o4-mini)

## Project Structure

```
src/
  config/       — environment configuration
  domain/       — Issue entity, metrics calculation
  services/
    jira/       — Jira client, data mapping, sprint insights
    analysis/   — prompt builder, OpenAI integration
    reporting/  — report formatter and publisher
  workflows/    — daily analysis orchestration
  scripts/      — dry-run, Jira simulation, inspection tools
```

## Quick Start

```bash
cp .env.example .env
# fill in JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN, JIRA_SOURCES, OPENAI_API_KEY

npm install
npm run dev
```

To test without network calls:
```bash
node --loader ts-node/esm src/scripts/dryRun.ts
```

## Configuration

Multi-project sources via `JIRA_SOURCES`:

```
kanban|kanban|KAN|project = "KAN" ORDER BY updated DESC|In Progress;scrum|scrum|SCRUM|project = "SCRUM" ORDER BY updated DESC|In Progress
```

Format: `key|methodology|projectKey|jql|startedStatuses`

If `JIRA_SOURCES` is not set, falls back to `JIRA_PROJECT_KEY` + `JIRA_JQL`.

If `OPENAI_API_KEY` is not set, the report is generated without AI analysis.

---

## RU — О проекте

Система автоматического анализа delivery-метрик на основе данных из Jira.

Забирает задачи из одного или нескольких Jira-проектов, считает Cycle Time, Lead Time, Throughput и Predictability отдельно для kanban и scrum, строит структурированный delivery snapshot и отправляет его в OpenAI для генерации actionable отчёта.

**Для scrum** — predictability считается от commitment активного спринта через Jira Agile API, а не от raw scope.

Проект демонстрирует: интеграцию с реальными API, доменное моделирование, разделение на слои (ingestion → metrics → analysis → reporting), и практическое применение LLM в delivery-автоматизации.

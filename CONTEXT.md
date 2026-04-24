# AI Delivery Analyst — Project Context

Используется для загрузки в AI-агента как стартовый контекст.

---

## Repository

https://github.com/Quietsilk/AI-Delivery-Analyst

## Stack

TypeScript · Node.js 20 · Jira Cloud REST API · Jira Agile API · OpenAI Responses API (o4-mini) · Telegram Bot API

---

## What Is Built

Полный автоматический пайплайн: **Jira → метрики → AI анализ → Telegram отчёт.**

### Config — `src/config/env.ts`
Конфигурация через env. `JIRA_SOURCES` поддерживает несколько проектов:
`key|methodology|projectKey|jql|startedStatuses` через `;`.
Поля: `telegramBotToken`, `telegramChatId`, `slackWebhookUrl`, `openAiApiKey`, `openAiModel`, `openAiReasoningEffort`.

### Domain — `src/domain/`
- `Issue` — доменная модель: id, type, status, createdAt, startedAt, resolvedAt, assignee, estimate, storyPoints, reopened
- `calculateMetrics` — Cycle Time, Lead Time, Throughput, Predictability, backlogSize, inProgressCount, completedCount

### Jira — `src/services/jira/`
- `JiraClient` — REST API клиент с пагинацией и changelog expand
- `mapIssue` — маппинг raw Jira issue в доменную модель; startedAt из changelog по startedStatuses; определение reopened
- `agileInsights` — Jira Agile API: board по projectKey, active sprint, predictability от commitment (completedCommitted / committed)

### Analysis — `src/services/analysis/`
- `DeliveryAnalyst` — вызов OpenAI Responses API `/v1/responses` с reasoning effort; graceful skip при 429/402 и при отсутствии ключа
- `buildPrompt` — structured prompt: aggregate метрики + per-source breakdown (kanban vs scrum) + active sprint контекст + sample открытых задач

### Reporting — `src/services/reporting/`
- `ReportFormatter` — отчёт с эмодзи, секциями (Overview / Sources / AI Analysis), цветовыми индикаторами 🟢🟡🔴, метрики в днях
- `ReportPublisher` — Telegram (sendMessage, chunking 4096 символов) или Slack (webhook); роутинг по `REPORT_CHANNEL`

### Orchestration — `src/workflows/runDailyDeliveryAnalysis.ts`
fetch issues → scrum insight → metrics → AI → format → publish

### Scripts — `src/scripts/`
- `dryRun.ts` — полный прогон на mock данных без сети
- `simulateJira.ts` — создание тестовых задач и движение по статусам
- `inspectJira.ts` — инспекция живых Jira данных

---

## Current .env Config

| Variable | Value |
|---|---|
| JIRA_BASE_URL | https://nhcompany.atlassian.net |
| JIRA_EMAIL | melnikov.lives@gmail.com |
| JIRA_SOURCES | TESTKANBAN (kanban), TESTSCRUM (scrum) |
| OPENAI_MODEL | o4-mini |
| OPENAI_REASONING_EFFORT | medium |
| REPORT_CHANNEL | telegram |
| TELEGRAM_BOT | @delivery_analyst_bot |

---

## What Is Not Done

- OpenAI токены не куплены — AI анализ скипается gracefully, отчёт всё равно уходит
- n8n workflow заготовки есть в `/n8n`, не подключены
- Slack не тестировался

## Suggested Next Steps

1. Пополнить OpenAI баланс → запустить полный цикл с AI анализом
2. Подключить n8n как cron orchestrator для daily run
3. Добавить группу Telegram вместо личной переписки
4. Расширить метрики: flow efficiency, aging WIP, blocked issues

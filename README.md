# AI Delivery Analyst

Базовый каркас проекта под MVP из ТЗ: сбор Jira-данных, расчёт delivery-метрик, AI-анализ и отправка отчёта.

## What This Project Demonstrates

Этот репозиторий можно показывать как практический пример delivery automation в IT:

- интеграция с Jira Cloud API для получения delivery-данных
- нормализация сырых Jira issues в доменную модель
- расчёт delivery metrics по нескольким delivery contexts
- поддержка разных методологий: `kanban` и `scrum`
- подготовка AI-ready контекста для автоматического delivery-анализа
- архитектурное мышление: разделение на ingestion, metrics, analysis и reporting layers

## Why It Is Valuable For A Resume

Проект показывает не только умение писать код, но и умение:

- переводить delivery-потребность в техническую архитектуру
- проектировать automation вокруг Jira и delivery-процессов
- работать с реальными API, конфигурируемыми источниками и operational risks
- строить систему, которую можно развивать в сторону отчётности, AI insights и workflow automation

## Project Structure

- `src/app` — orchestration и use-case слой
- `src/config` — конфигурация окружения
- `src/domain` — сущности и доменная логика
- `src/services/jira` — клиент Jira и маппинг данных
- `src/services/analysis` — подготовка AI prompt и анализ
- `src/services/reporting` — форматирование и доставка отчётов
- `src/workflows` — сценарий полного daily-run
- `n8n` — заготовки workflow под автоматизацию
- `docs` — архитектурные и продуктовые заметки
- `tests` — место для unit/integration тестов

## Suggested Next Steps

1. Подключить реальные environment variables и секреты.
2. Уточнить кастомные Jira fields для story points и start status transitions.
3. Добавить расчёт cycle time, lead time, throughput и predictability по выбранному периоду.
4. Подключить LLM provider и каналы доставки отчётов.
5. Перенести бизнес-флоу в n8n или использовать его как orchestrator над сервисом.

## Current Vertical Slice

Сейчас проект уже покрывает минимальный сценарий:

1. Берёт задачи из одного или нескольких Jira sources.
2. Нормализует их в доменную модель `Issue`.
3. Считает базовые delivery metrics по каждому source и в aggregate.
4. Передаёт delivery snapshot с учётом `scrum`/`kanban` контекста в OpenAI Responses API.
5. Формирует текстовый отчёт и публикует его в stdout.

## Current Delivery Model

- `kanban` sources интерпретируются как flow-oriented contexts с акцентом на `backlog`, `in progress`, `throughput`, `lead time`, `cycle time`
- `scrum` sources уже учитываются на уровне архитектуры и отчётности
- для `scrum` подключён Jira Agile API enrichment
- если у scrum board есть active sprint, `predictability` считается как `completed committed / committed`
- если active sprint ещё не запущен, система явно сообщает, что использует временный scope-based proxy

## Multi-Project Delivery Sources

Для архитектурной поддержки разных методологий используется `JIRA_SOURCES`.

Формат:

`sourceKey|methodology|projectKey|jql|startedStatus1,startedStatus2;sourceKey2|methodology|projectKey|jql|startedStatus`

Пример:

`kanban|kanban|KAN|project = "KAN" ORDER BY updated DESC|In Progress;scrum|scrum|SCRUM|project = "SCRUM" ORDER BY updated DESC|In Progress`

Если `JIRA_SOURCES` не задан, используется одиночный source из `JIRA_PROJECT_KEY` и `JIRA_JQL`.

## Jira Simulation

Для проверки системы на псевдо-спринтах и flow-сценариях можно запускать симуляцию Jira-работы:

- `npm run jira:simulate` — прогоняет сценарии для всех источников
- `npm run jira:simulate kanban` — только kanban sources
- `npm run jira:simulate scrum` — только scrum sources

Симулятор:

- создаёт тестовые задачи в Jira
- двигает их по статусам
- оставляет часть задач незавершёнными
- формирует более реалистичный датасет для проверки метрик и отчётов

Это полезно и для разработки, и для демонстрации проекта как portfolio piece.

## OpenAI Notes

- По умолчанию analysis-слой использует `Responses API`.
- Модель и reasoning effort задаются через `OPENAI_MODEL` и `OPENAI_REASONING_EFFORT`.
- Если `OPENAI_API_KEY` не задан, отчёт всё равно соберётся, но AI-анализ будет пропущен.

## Suggested Portfolio Positioning

Если использовать репозиторий в резюме или LinkedIn, его можно описывать как:

`Built an AI-assisted delivery analytics prototype that pulls Jira data, calculates multi-project delivery metrics, distinguishes scrum vs kanban delivery contexts, and prepares actionable reporting for engineering leadership.`

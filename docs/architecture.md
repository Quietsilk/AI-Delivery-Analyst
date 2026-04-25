# Architecture

## Обзор

```
Browser (dashboard.html)
    │
    │  POST /webhook/sync-report
    │  { baseUrl, email, apiToken, jql, period }
    ▼
server.py (Python stdlib HTTP)
    │
    ├── fetch_jira()
    │       │
    │       ├── POST /rest/api/3/search/jql   (пагинация, PAGE_SIZE=50)
    │       └── GET  /rest/api/3/issue/{key}/changelog
    │               (для всех задач)
    │
    ├── calculate_metrics(issues, cutoff)
    │       ├── Cycle Time (последний started_at → resolved_at)
    │       ├── Lead Time  (created_at → resolved_at)
    │       ├── Throughput (кол-во resolved за период)
    │       └── Backlog / WIP / Reopened counts (Reopened — только среди completed)
    │
    ├── call_openai()          [опционально]
    │       └── POST /v1/responses (o4-mini, reasoning medium)
    │
    ├── send_telegram()        [опционально]
    │       └── POST /bot{token}/sendMessage (с чанкингом ≤4096)
    │
    └── JSON response → Browser
            { ok, dashboard: { metrics..., analysis, aiEnabled } }
```

---

## Принципы

**Метрики детерминированы.** Всё считается из changelog Jira по явным правилам. AI не участвует в расчётах.

**AI — интерпретатор, не калькулятор.** Если ключ не задан — метрики работают полностью, AI-панели показывают подсказку.

**Period-фильтр server-side.** Cutoff применяется к `resolved_at` завершённых задач. In Progress и Backlog всегда актуальные (без фильтра).

**Zero-dependency backend.** server.py использует только stdlib Python 3.9+. Установка не нужна.

---

## Слои данных

```
Jira Raw Issue
    └── fields: status, created, resolutiondate
    └── changelog.histories[].items[field="status"]
            │
            ▼
    Mapped Issue (dict)
            started_at   ← последний переход в STARTED перед last_done
            resolved_at  ← resolutiondate или последний переход в DONE
            created_at   ← fields.created
            reopened     ← был ли переход DONE → не-DONE
            │
            ▼ (+ cutoff filter)
    Metrics dict
            cycleTimeDays, leadTimeDays, throughput,
            backlogSize, inProgressCount,
            reopenedCount (только среди completed)
```

---

## Статусная модель

Сравнения case-insensitive:

```python
STARTED = {"in progress", "selected for development", "в работе", "in development"}
DONE    = {"done", "closed", "resolved", "выполнено", "complete"}
```

Changelog запрашивается для **всех** задач. Это необходимо для корректного определения задач в Done без `resolutiondate` (BUG-1) и задач, вернувшихся из In Progress в Backlog (BUG-4).

---

## Frontend (dashboard.html)

Однофайловый, без сборки, без фреймворков.

**LocalStorage-ключи:**

| Ключ | Содержимое |
|---|---|
| `ada:baseUrl` | Jira URL |
| `ada:email` | Jira email |
| `ada:token` | Jira API token |
| `ada:projects` | JSON: массив проектных табов |
| `ada:activeId` | ID активного проекта |
| `ada:period` | Активный period-фильтр |
| `ada:runHistory` | JSON: последние 30 синков (ts + cycleTimeDays + throughput) |
| `ada:sidebarCollapsed` | Булево: состояние сайдбара |

---

## Масштабирование (следующие шаги)

При росте сложности — разбить `server.py` на модули:

```
server.py      → app.py (роутинг)
               + jira.py (fetch, pagination)
               + metrics.py (calculate_metrics)
               + ai.py (call_openai)
               + telegram.py (send_telegram, chunking)
```

При появлении scheduled runs — добавить Flask + APScheduler или cron.
При необходимости multi-source — расширить `_handle` для массива источников.

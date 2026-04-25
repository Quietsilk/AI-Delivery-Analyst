# Architecture

## Обзор

```
Browser (dashboard.html — read-only UI)
    │
    ├── GET  /latest?project=KEY       ← читает последний снапшот
    ├── GET  /history?project=KEY&period=30d  ← читает историю
    └── POST /sync  { project, creds, jql }  ← запускает ингест в фоне
            │
            ▼
server.py  (тонкий HTTP-роутер)
            │
            ├── server/api.py          ← handle_get_latest, handle_get_history, handle_post_sync
            │
            ├── server/ingestion.py    ← fetch_jira → calculate_metrics → save_snapshot
            │       │
            │       ├── server_app.fetch_jira()
            │       │       ├── POST /rest/api/3/search/jql  (пагинация, PAGE_SIZE=50)
            │       │       └── GET  /rest/api/3/issue/{key}/changelog  (параллельно, 10 потоков)
            │       │
            │       └── server/metrics.py → calculate_metrics(issues)
            │               ├── Cycle Time        (последний started_at → resolved_at)
            │               ├── Time to Market    (created_at → resolved_at)
            │               ├── Flow Efficiency   (cycleTime / timeToMarket × 100, cap 100%)
            │               ├── Throughput        (выставляется в ingestion, не в metrics)
            │               └── Backlog / WIP / Reopened
            │
            ├── server/storage.py      ← SQLite CRUD
            │       └── snapshots(id, project_key, timestamp, metrics_json)
            │
            └── server/scheduler.py   ← daemon-поток, запускает ingestion по расписанию
                    └── SYNC_INTERVAL_SECONDS (default 3600)
```

---

## Архитектурные инварианты

**Инвариант 1 — UI read-only.**
Браузер никогда не инициирует расчёт метрик. Он только читает сохранённые снапшоты. Метрики считаются один раз при ingestion и сохраняются.

**Инвариант 2 — Иммутабельные снапшоты.**
Каждый запуск ingestion создаёт новую строку в SQLite. Никаких UPDATE/DELETE.

**Инвариант 3 — Throughput = дельта снапшотов.**
`throughput` = количество задач, resolved с момента предыдущего снапшота. Вычисляется в `ingestion.py`, не в `metrics.py`.

**Инвариант 4 — Period без пересчёта.**
`GET /history?period=30d` фильтрует строки SQLite по полю `timestamp`. Метрики не пересчитываются.

**Инвариант 5 — `calculate_metrics` без `period`.**
Функция `calculate_metrics(issues)` не принимает `cutoff`/`period` в сигнатуре.

---

## SQLite-схема

```sql
CREATE TABLE snapshots (
    id           INTEGER PRIMARY KEY,
    project_key  TEXT NOT NULL,
    timestamp    TEXT NOT NULL,   -- ISO 8601
    metrics_json TEXT NOT NULL    -- JSON: cycleTimeDays, throughput, …
);
```

Данные только добавляются (INSERT). История хранится бессрочно.

---

## Пакет server/

| Модуль | Экспортирует | Назначение |
|---|---|---|
| `metrics.py` | `calculate_metrics(issues)` | Чистая функция, нет side-эффектов |
| `storage.py` | `init_db`, `save_snapshot`, `get_latest`, `get_history`, `get_previous_snapshot` | SQLite CRUD |
| `ingestion.py` | `run_ingestion(project_key, base_url, email, api_token, jql, db_path)` | Полный pipeline: fetch → metrics → throughput delta → save |
| `api.py` | `handle_get_latest`, `handle_get_history`, `handle_post_sync` | HTTP handlers |
| `scheduler.py` | `start_scheduler(projects, db_path, interval)` | Daemon-поток |

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
            ▼
    Metrics dict
            cycleTimeDays, timeToMarketDays, flowEfficiencyPercent,
            throughput (выставляется ingestion), backlogSize,
            inProgressCount, reopenedCount
            │
            ▼
    SQLite snapshot
            project_key, timestamp, metrics_json
            │
            ▼  GET /latest или GET /history
    Browser (dashboard.html)
            updateDashboard(metrics) + drawChart(snapshots)
```

---

## Frontend (dashboard.html)

Однофайловый, без сборки, без фреймворков. Read-only UI.

**Ключевые функции:**

| Функция | Что делает |
|---|---|
| `refreshDashboard()` | GET /latest → updateDashboard + loadHistory; при 404 — auto-trigger POST /sync + polling |
| `loadHistory()` | GET /history → drawChart + drawThroughputChart |
| `_postSync()` | POST /sync — запускает фоновый ингест |
| `_pollLatest(attempts)` | Поллинг GET /latest каждые 3s (до 20 попыток = ~60s) |
| `updateDataAge(ts)` | Показывает "Updated Xm ago" в статус-строке |
| `switchProject(id)` | Переключает таб → сбрасывает prevKpi → вызывает refreshDashboard |
| `drawChart(snapshots)` | Рисует SVG-тренд Cycle Time из массива `{timestamp, metrics}` |
| `drawThroughputChart(snapshots)` | Рисует SVG-тренд Throughput |

**LocalStorage-ключи:**

| Ключ | Содержимое |
|---|---|
| `ada:baseUrl` | Jira URL |
| `ada:email` | Jira email |
| `ada:token` | Jira API token |
| `ada:projects` | JSON: массив проектных табов |
| `ada:activeId` | ID активного проекта |
| `ada:period` | Активный period-фильтр |
| `ada:sidebarCollapsed` | Булево: состояние сайдбара |

`ada:runHistory` **удалён** — история хранится в SQLite, читается через API.

---

## Auto-sync flow

```
refreshDashboard()
    │
    GET /latest?project=KEY
    │
    ├── 200 → updateDashboard(metrics) + loadHistory()
    │
    └── 404 → POST /sync (тихо)
                │
                _pollLatest(attempts=0)
                │
                каждые 3s: GET /latest
                │
                ├── 200 → refreshDashboard()  ← данные готовы
                └── 404 → _pollLatest(attempts+1)  ← ждём ещё
                           (до 20 попыток = ~60s, затем timeout)
```

---

## Статусная модель Jira

```python
STARTED = {"in progress", "selected for development", "в работе", "in development"}
DONE    = {"done", "closed", "resolved", "выполнено", "complete"}
```

Все сравнения case-insensitive (`.lower()`). Changelog запрашивается для всех задач.

---

## Legacy

`server_app.py` (переименован из старого `server.py`) — сохранён для обратной совместимости. Эндпоинт `POST /webhook/sync-report` делегирует сюда. Не удалять — используется в legacy-интеграциях.

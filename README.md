# AI Delivery Analyst

Система раннего обнаружения рисков доставки. Подключается к Jira, рассчитывает метрики из changelog, анализирует через OpenAI и отображает всё в браузерном дашборде — с фоновым синком и персистентным хранением снапшотов.

---

## Что делает

1. Забирает задачи из Jira по JQL (cursor-based пагинация)
2. Загружает changelog каждой задачи параллельно (10 потоков)
3. Рассчитывает delivery-метрики: Cycle Time, Time to Market, Flow Efficiency, Throughput, Reopened
4. Сохраняет снапшот в SQLite (иммутабельно — только INSERT)
5. Анализирует метрики через OpenAI → Summary, Risks, Actions (опционально)
6. Дашборд читает снапшоты через REST API (read-only UI)
7. Фоновый планировщик автоматически синхронизирует проекты по расписанию

---

## Quick start

```bash
# 1. Clone
git clone https://github.com/Quietsilk/AI-Delivery-Analyst
cd AI-Delivery-Analyst

# 2. Configure (AI и Telegram опциональны)
cp .env.example .env

# 3. Run
python3 server.py
# → http://localhost:5678
```

Jira credentials вводятся в дашборде и хранятся в localStorage браузера.

---

## Стек

- **Python 3.9+** — stdlib-only, zero dependencies
- **SQLite** — персистентное хранение снапшотов через `server/storage.py`
- **HTML/CSS/JS** — однофайловый дашборд, read-only UI
- **Jira Cloud REST API** — `/rest/api/3/search/jql` + `/rest/api/3/issue/{key}/changelog`
- **OpenAI Responses API** — модель `o4-mini`, опционально

---

## Структура проекта

```
ai-delivery-analyst/
├── server.py                          # Тонкий HTTP-роутер
├── server_app.py                      # Legacy pipeline (backward compat)
├── server/
│   ├── __init__.py
│   ├── metrics.py                     # calculate_metrics(issues) — чистая функция
│   ├── storage.py                     # SQLite CRUD (init, save, get_latest, get_history)
│   ├── ingestion.py                   # fetch + metrics + throughput delta + save
│   ├── api.py                         # HTTP handlers (GET /latest, GET /history, POST /sync)
│   └── scheduler.py                   # Фоновый daemon-поток для автосинка
├── ai-delivery-analyst-dashboard.html # UI (single file, read-only)
├── tests/
│   ├── test_server.py                 # 87 regression тестов (legacy)
│   ├── test_metrics.py                # 15 тестов
│   ├── test_storage.py                # 13 тестов
│   ├── test_ingestion.py              # 8 тестов
│   └── test_api.py                    # 8 тестов (108 итого)
├── docs/
│   ├── architecture.md
│   ├── backlog.md
│   └── risks.md
├── specs/                             # Версионированные ТЗ
├── .env.example
└── .env                               # Локальные секреты (не в git)
```

---

## API

| Метод | Путь | Описание |
|---|---|---|
| `GET` | `/` | Дашборд HTML |
| `GET` | `/latest?project=KEY` | Последний снапшот проекта |
| `GET` | `/history?project=KEY&period=7d\|30d\|90d` | История снапшотов |
| `POST` | `/sync` | Запустить ингест в фоне → `{ok, queued}` |
| `POST` | `/webhook/sync-report` | Legacy endpoint (deprecated) |

**GET /latest** — пример ответа:
```json
{
  "ok": true,
  "snapshot": {
    "timestamp": "2026-04-25T12:00:00",
    "metrics": {
      "cycleTimeDays": 4.2,
      "throughput": 23,
      "timeToMarketDays": 8.7,
      "reopenedCount": 0,
      "flowEfficiencyPercent": 48.3
    }
  }
}
```

**POST /sync** — пример запроса:
```json
{
  "project": "KEY",
  "baseUrl": "https://company.atlassian.net",
  "email": "you@company.com",
  "apiToken": "...",
  "jql": "project = KEY ORDER BY updated DESC"
}
```

---

## Переменные окружения

| Переменная | Назначение | По умолчанию |
|---|---|---|
| `DB_PATH` | Путь к SQLite-файлу | `snapshots.db` |
| `SYNC_INTERVAL_SECONDS` | Интервал фонового синка | `3600` |
| `PROJECTS` | JSON-массив проектов для планировщика | `[]` |
| `OPENAI_API_KEY` | AI-анализ (опционально) | — |
| `TELEGRAM_BOT_TOKEN` | Telegram (опционально, legacy) | — |
| `TELEGRAM_CHAT_ID` | Telegram (опционально, legacy) | — |

**Пример PROJECTS:**
```json
[{"project":"KEY","baseUrl":"https://co.atlassian.net","email":"x@co.com","apiToken":"...","jql":"project=KEY"}]
```

---

## Метрики

Все метрики рассчитываются из Jira changelog — не из статических полей.

| Метрика | Определение | Хорошо | Плохо |
|---|---|---|---|
| **Cycle Time** | Среднее время от последнего "In Progress" до Done | ≤ 5d | ≥ 10d |
| **Time to Market** | Среднее время от создания до Done | ≤ 10d | ≥ 20d |
| **Flow Efficiency** | cycleTime / timeToMarket × 100%, кап 100% | ≥ 40% | ≤ 15% |
| **Throughput** | Кол-во resolved с предыдущего снапшота | > 0 | = 0 |
| **Reopened** | Задачи, вернувшиеся из Done | = 0 | > 2 |

---

## Тесты

```bash
python3 -m unittest discover -s tests -v
```

108 тестов, zero external dependencies:

| Файл | Тестов | Покрытие |
|---|---|---|
| `test_server.py` | 87 | Legacy pipeline |
| `test_metrics.py` | 15 | `calculate_metrics` — edge cases, flow efficiency, parse_dt |
| `test_storage.py` | 13 | SQLite CRUD, иммутабельность, фильтрация по периоду |
| `test_ingestion.py` | 8 | Throughput delta, первый/второй снапшот |
| `test_api.py` | 8 | HTTP handlers, 400/404/202 статусы |

---

## Архитектурные инварианты

1. **UI read-only** — браузер только читает снапшоты, никогда не считает метрики
2. **Иммутабельные снапшоты** — только INSERT в SQLite, никогда UPDATE/DELETE
3. **Throughput = дельта** — кол-во resolved с `timestamp` предыдущего снапшота
4. **Period без пересчёта** — `GET /history?period=30d` фильтрует строки по timestamp
5. **`calculate_metrics` без period** — чистая функция, нет параметров cutoff/period

---

## Built with AI

Проект создан с использованием Claude (Anthropic) как основного инструмента разработки — итеративное написание ТЗ, генерация кода, обнаружение багов, написание тестов и QA.

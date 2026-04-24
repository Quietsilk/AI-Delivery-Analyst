# AI Delivery Analyst — Project Context

Стартовый контекст для AI-агента. Актуально на апрель 2026.

---

## Repository

https://github.com/Quietsilk/AI-Delivery-Analyst

## Стек

Python 3.9+ · stdlib only (http.server, urllib, json) · Jira Cloud REST API · OpenAI Responses API (o4-mini) · Telegram Bot API · Vanilla JS/HTML дашборд

---

## Архитектура

Два компонента:

**`server.py`** — Python HTTP-сервер без зависимостей:
- `GET /` → отдаёт `ai-delivery-analyst-dashboard.html`
- `POST /webhook/sync-report` → полный pipeline: Jira → метрики → OpenAI → Telegram → JSON-ответ

**`ai-delivery-analyst-dashboard.html`** — однофайловый браузерный UI:
- Вводит Jira credentials (хранит в localStorage)
- Управляет проектными табами и JQL
- Period-фильтр (7d / 30d / 90d / All)
- Визуализирует KPI, риски, действия, chart

---

## Ключевые модули server.py

| Функция | Что делает |
|---|---|
| `fetch_jira()` | Пагинация (`PAGE_SIZE=50`), отдельный changelog для resolved + in-progress |
| `calculate_metrics(issues, cutoff)` | Cycle Time, Lead Time, Throughput, Predictability, Backlog, WIP, Reopened |
| `_parse_dt(s)` | ISO 8601 → datetime, обрабатывает Z и +00:00 |
| `call_openai(metrics, api_key, period_label)` | OpenAI Responses API, o4-mini |
| `send_telegram(text, token, chat_id)` | Умный split по `\n` / ` ` / hard cut |
| `_split_telegram(text, max_len)` | Чанкинг Telegram-сообщений ≤4096 символов |
| `load_env(path)` | Парсит .env без зависимостей |

---

## Статусы

```python
STARTED = {"in progress", "selected for development", "в работе", "in development"}
DONE    = {"done", "closed", "resolved", "выполнено", "complete"}
```

Все сравнения — **case-insensitive** (`.lower()`).

---

## Переменные окружения (server.py)

| Переменная | Назначение |
|---|---|
| `OPENAI_API_KEY` | AI-анализ (опционально) |
| `TELEGRAM_BOT_TOKEN` | Отправка отчётов (опционально) |
| `TELEGRAM_CHAT_ID` | Получатель Telegram (опционально) |

Jira credentials → UI → localStorage (не в .env).

---

## Тесты

`tests/test_server.py` — 33 теста, stdlib unittest.

```bash
python3 -m unittest tests/test_server.py
```

---

## Известные ограничения

- Статусы STARTED/DONE — хардкод в server.py (не конфигурируются через UI)
- Нет хранилища истории синков (только в памяти браузера через localStorage, ≤30 записей)
- Один проект на синк (multi-source не реализован)
- Нет scheduled/cron запуска — только ручной синк через UI

---

## Что сделано (хронология)

1. TypeScript-прототип (src/) — выпилен в пользу Python (коммит `6d88e48`)
2. Python stdlib HTTP-сервер + однофайловый HTML-дашборд
3. Jira API: POST /search/jql + отдельный changelog fetch
4. Пагинация (PAGE_SIZE=50, isLast loop)
5. Period-фильтр (7d/30d/90d/all) — server-side cutoff по resolved_at
6. localStorage-персистентность (credentials, projects, history)
7. Case-insensitive статусы (BUG-S01)
8. Smart Telegram chunking (BUG-S04 port)
9. Regression suite (33 тестов)

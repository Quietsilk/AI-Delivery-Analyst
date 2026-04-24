# AI Delivery Analyst

Система раннего обнаружения delivery-рисков. Подключается к Jira, считает метрики из changelog, анализирует через AI и отправляет отчёт в Telegram — без ручного труда.

---

## Что делает

1. Получает задачи из Jira по JQL-запросу (cursor-based пагинация)
2. Параллельно загружает changelog для каждой задачи (до 10 потоков)
3. Вычисляет delivery-метрики: Cycle Time, Lead Time, Throughput, Done Rate, Reopened
4. Фильтрует завершённые задачи по периоду (7d / 30d / 90d / All)
5. Анализирует метрики через OpenAI → Summary, Risks, Actions
6. Отправляет отчёт в Telegram (умный чанкинг ≤4096 символов)
7. Отображает всё в браузерном дашборде в реальном времени

---

## Быстрый старт

```bash
# 1. Клонировать
git clone https://github.com/Quietsilk/AI-Delivery-Analyst
cd AI-Delivery-Analyst

# 2. Настроить окружение (AI и Telegram — опционально)
cp .env.example .env
# Отредактировать .env

# 3. Запустить
./start.sh
# → http://localhost:5678
```

Credentials Jira (URL, email, API token) вводятся прямо в дашборде и сохраняются в localStorage.

---

## Стек

- **Python 3.9+** — сервер на stdlib, без зависимостей (`pip install` не нужен)
- **HTML/CSS/JS** — однофайловый дашборд, работает в браузере
- **Jira Cloud REST API** — `/rest/api/3/search/jql` + `/rest/api/3/issue/{key}/changelog`
- **OpenAI Responses API** — модель `o4-mini`, опционально
- **Telegram Bot API** — доставка отчётов, опционально

---

## Структура проекта

```
ai-delivery-analyst/
├── server.py                          # HTTP-сервер: роутинг, Jira, метрики, OpenAI, Telegram
├── ai-delivery-analyst-dashboard.html # UI (однофайловый)
├── start.sh                           # Обёртка запуска
├── tests/
│   └── test_server.py                 # 33 regression-теста (stdlib unittest)
├── docs/
│   ├── architecture.md
│   ├── backlog.md
│   └── risks.md
├── .env.example                       # Шаблон переменных окружения
└── .env                               # Локальные секреты (не в git)
```

---

## Переменные окружения

| Переменная | Описание | Обязательна |
|---|---|---|
| `OPENAI_API_KEY` | Ключ OpenAI для AI-анализа | Нет |
| `TELEGRAM_BOT_TOKEN` | Токен Telegram-бота | Нет |
| `TELEGRAM_CHAT_ID` | ID чата или группы Telegram | Нет |

Jira credentials вводятся в UI и не хранятся на сервере.

---

## Метрики

Все метрики вычисляются из changelog Jira — не из статических полей.

| Метрика | Определение |
|---|---|
| **Cycle Time** | Среднее время от последнего перехода в "In Progress" до завершения |
| **Lead Time** | Среднее время от создания задачи до завершения |
| **Throughput** | Количество завершённых задач за выбранный период (отображается с меткой: "15 / 30d") |
| **Done Rate** | Завершённые / все задачи в выборке × 100% |
| **Reopened** | Количество завершённых задач, которые ранее возвращались из Done |

Определение статусов (case-insensitive):

```python
STARTED = {"in progress", "selected for development", "в работе", "in development"}
DONE    = {"done", "closed", "resolved", "выполнено", "complete"}
```

---

## Period-фильтр

Фильтр применяется **только к завершённым задачам** по дате `resolved_at`.  
In Progress и Backlog всегда отражают актуальное состояние независимо от периода.

---

## AI-анализ

Если `OPENAI_API_KEY` задан, сервер вызывает `o4-mini` и возвращает:

- **Summary** — 1-2 предложения о состоянии доставки
- **Risks** — конкретные риски с причинами
- **Actions** — 3 рекомендованных действия

Состояния AI в дашборде:

| Состояние | Причина | Что показывает UI |
|---|---|---|
| Анализ готов | OpenAI ответил | Summary, Risks, Actions |
| `AI unavailable: ...` | Ошибка API (429, timeout) | Текст ошибки во всех трёх панелях |
| `AI not configured` | `OPENAI_API_KEY` не задан | Подсказка в панелях |

---

## Jira API

Сервер использует новый `/rest/api/3/search/jql` endpoint (Jira Cloud):

- `fieldsByKeys: true` обязателен для получения `key` и именованных полей
- Пагинация через `nextPageToken` (cursor-based, не offset)
- Changelog загружается параллельно (до 10 потоков) для ускорения

---

## Тесты

```bash
python3 -m unittest tests/test_server.py -v
```

37 тестов без внешних зависимостей. Покрытие:

| Группа | Тестов |
|---|---|
| `calculate_metrics` — пустой список, completed, WIP, backlog, cutoff, reopened, cycle/lead time, BUG-1/2/3 | 14 |
| `_split_telegram` — короткий текст, split по newline/space, hard cut, пустые чанки | 7 |
| `fetch_jira` — одна страница, cursor pagination, остановка по размеру страницы | 3 |
| HTTP-интеграция — GET, 404, CORS, POST pipeline, 500 на ошибке Jira, period=7d, throughputPeriodLabel | 8 |
| `_parse_dt` — форматы Z, +00:00, +HH:MM | 3 |
| `load_env` — загрузка файла, отсутствующий файл | 2 |

---

## Известные ограничения

- Статусы STARTED/DONE задаются в коде `server.py` (не конфигурируются через UI)
- История синков хранится только в localStorage браузера (до 30 записей)
- Один JQL-запрос на синк (multi-source не реализован)
- Нет scheduled/cron запуска — только ручной синк через UI

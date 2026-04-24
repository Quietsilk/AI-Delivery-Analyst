# AI Delivery Analyst

Система раннего обнаружения delivery-рисков. Подключается к Jira, считает метрики, анализирует с помощью AI и отправляет отчёт в Telegram — без ручного труда.

---

## Что делает

1. Получает задачи из Jira по JQL-запросу (с пагинацией)
2. Вычисляет delivery-метрики из changelog: Cycle Time, Lead Time, Throughput, Predictability
3. Фильтрует по периоду (7d / 30d / 90d / All)
4. Анализирует метрики через OpenAI → структурированные риски и действия
5. Отправляет отчёт в Telegram
6. Отображает всё в браузерном дашборде

---

## Стек

- **Python 3.9+** — сервер на stdlib, без зависимостей
- **HTML/CSS/JS** — однофайловый дашборд
- **Jira Cloud REST API** — `/rest/api/3/search/jql` + `/rest/api/3/issue/{key}/changelog`
- **OpenAI Responses API** — `o4-mini`, опционально
- **Telegram Bot API** — доставка отчётов, опционально

---

## Быстрый старт

```bash
cp .env.example .env
# Заполни .env (минимум: только OPENAI_API_KEY если нужен AI-анализ)

python3 server.py
# → http://localhost:5678
```

Credentials Jira вводятся прямо в дашборде и сохраняются в localStorage.

---

## Структура проекта

```
ai-delivery-analyst/
├── server.py          # HTTP-сервер: роутинг, Jira, метрики, OpenAI, Telegram
├── ai-delivery-analyst-dashboard.html  # UI (однофайловый)
├── start.sh           # Обёртка запуска
├── tests/
│   └── test_server.py # 33 regression-теста (stdlib unittest)
├── docs/
│   ├── architecture.md
│   ├── backlog.md
│   └── risks.md
├── .env               # Локальные секреты (не в git)
└── .env.example       # Шаблон
```

---

## Переменные окружения

| Переменная | Описание | Обязательна |
|---|---|---|
| `OPENAI_API_KEY` | Ключ OpenAI для AI-анализа | Нет |
| `TELEGRAM_BOT_TOKEN` | Токен бота для отправки отчётов | Нет |
| `TELEGRAM_CHAT_ID` | ID чата / группы Telegram | Нет |

Jira credentials (URL, email, API token) и JQL вводятся в UI и хранятся в localStorage браузера.

---

## Метрики

Все метрики считаются из changelog Jira — не из статических полей.

| Метрика | Определение |
|---|---|
| **Cycle Time** | Время от первого перехода в "In Progress" до завершения |
| **Lead Time** | Время от создания задачи до завершения |
| **Throughput** | Количество завершённых задач за период |
| **Predictability** | Завершённые за период / все задачи в выборке × 100% |

Статусы "в работе" и "завершено" определяются case-insensitive.

---

## Фильтр периода

Period-фильтр применяется только к завершённым задачам (`resolved_at`).
In Progress и Backlog всегда показывают актуальное состояние.

---

## Тесты

```bash
python3 -m unittest tests/test_server.py -v
```

33 теста, без внешних зависимостей. Покрытие: метрики, пагинация, Telegram-чанкинг, HTTP-интеграция, period-фильтр.

---

## AI-анализ

Если `OPENAI_API_KEY` задан — сервер вызывает `o4-mini` и возвращает:
- **Summary** — 1-2 предложения о состоянии доставки
- **Risks** — конкретные риски с причинами
- **Actions** — 3 действия

Если ключ не задан — метрики работают в полном объёме, AI-панели показывают подсказку.

---

## Telegram

Отчёт отправляется автоматически после каждого синка (если настроен бот).
Длинные отчёты разбиваются на чанки по границам строк — без обрыва слов.

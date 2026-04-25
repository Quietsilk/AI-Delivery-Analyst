# Backlog

## В работе / ближайшее

- [ ] Настройка scheduled daily run (cron или launchd)
- [ ] Multi-source: несколько Jira-проектов в одном синке с агрегированными метриками
- [ ] Конфигурация STARTED/DONE статусов через UI (сейчас — хардкод в server.py)

## Метрики и аналитика

- [ ] Flow efficiency (active time / lead time)
- [ ] Aging WIP — задачи в In Progress дольше threshold
- [ ] Blocked issues — детектирование по метке или статусу
- [ ] Trend по периодам (сравнение 30d vs предыдущие 30d)
- [ ] Story points в метриках (velocity, scope completion)

## Инфраструктура

- [ ] Разбивка server.py на модули (jira.py, metrics.py, ai.py, telegram.py) — при росте >500 строк
- [ ] Переход на Flask при появлении ≥2 новых эндпоинтов
- [ ] Persistent storage для истории синков (SQLite) — сейчас только localStorage
- [ ] Docker-образ для деплоя

## Интеграции

- [ ] Slack webhook (код заготовлен, не тестировался)
- [ ] Scrum: Jira Agile API для sprint predictability (был в TypeScript-прототипе)
- [ ] Экспорт отчёта в PDF / Confluence

## Готово ✅

- [x] UX overhaul: KPI-акценты, collapsible sidebar, empty state, period bar, AI/Risks иерархия, favicon
- [x] Автосинк при смене периода (без ручного нажатия Sync)
- [x] Восстановление connected-состояния при обновлении страницы
- [x] Подавление CSS-transition сайдбара при загрузке страницы (layout jerk)
- [x] Jira pagination (PAGE_SIZE=50, isLast loop)
- [x] Period-фильтр (7d/30d/90d/all), server-side cutoff
- [x] Changelog fetch для всех задач (покрывает Done без resolutiondate и In Progress → Backlog)
- [x] Case-insensitive статусная модель
- [x] localStorage-персистентность (credentials, projects, history, period)
- [x] Smart Telegram chunking (split по \n / пробел / hard cut)
- [x] aiEnabled флаг в ответе (честный placeholder при отсутствии ключа)
- [x] Regression suite: 61 тест, stdlib unittest, zero deps (добавлены call_openai, send_telegram, edge cases)
- [x] Архитектурный pivot: TypeScript → Python
- [x] Переименование Predictability → Done Rate (корректное определение метрики)
- [x] Throughput с меткой периода (15 / 30d) в UI и Telegram
- [x] KPI-карточка Reopened в дашборде (красная при > 0)
- [x] График тренда Throughput рядом с Cycle Time
- [x] BUG-1: Done без resolutiondate корректно попадает в Throughput
- [x] BUG-2: Cycle Time от последнего старта перед done, не от первого
- [x] BUG-3: Reopened фильтруется по периоду (только среди completed)
- [x] BUG-4: Задачи In Progress → Backlog видимы (changelog фетчится для всех)
- [x] BUG-5: Удалён дублирующий completedCount, оставлен throughput

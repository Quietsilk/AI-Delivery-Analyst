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

- [x] Jira pagination (PAGE_SIZE=50, isLast loop)
- [x] Period-фильтр (7d/30d/90d/all), server-side cutoff
- [x] Changelog fetch только для resolved + in-progress (не backlog)
- [x] Case-insensitive статусная модель
- [x] localStorage-персистентность (credentials, projects, history, period)
- [x] Smart Telegram chunking (split по \n / пробел / hard cut)
- [x] aiEnabled флаг в ответе (честный placeholder при отсутствии ключа)
- [x] Regression suite: 33 теста, stdlib unittest, zero deps
- [x] Архитектурный pivot: TypeScript → Python

# Backlog

## В работе / ближайшее

- [ ] Конфигурация STARTED/DONE статусов через UI (сейчас — хардкод в server_app.py)
- [ ] Multi-source: несколько Jira-проектов в одном синке с агрегированными метриками
- [ ] Full UI/UX redesign (visual hierarchy: hero KPI → secondary row → AI insight → actions → charts)

## Метрики и аналитика

- [ ] Aging WIP — задачи в In Progress дольше threshold
- [ ] Blocked issues — детектирование по метке или статусу
- [ ] Сравнение периодов (30d vs предыдущие 30d) на основе снапшотов
- [ ] Story points в метриках (velocity, scope completion)

## Инфраструктура

- [ ] Docker-образ для деплоя
- [ ] Migrate legacy `/webhook/sync-report` на новый pipeline (убрать блокирующий HTTP)
- [ ] Конфигурация PROJECTS через UI (сейчас только через env)
- [ ] Экспорт истории снапшотов в CSV / PDF

## Интеграции

- [ ] Scrum: Jira Agile API для sprint predictability
- [ ] Slack webhook (код заготовлен в legacy, не тестировался)
- [ ] Confluence: публикация отчёта

## Готово ✅

- [x] Tab switch: переключение проекта автоматически загружает данные (`switchProject` async + `refreshDashboard`)
- [x] Архитектурный рефакторинг (апрель 2026): `server/` пакет, SQLite, read-only UI, 108 тестов
- [x] Persistent storage: SQLite снапшоты, иммутабельные строки, история бессрочно
- [x] Background scheduler: daemon-поток, `PROJECTS` env, `SYNC_INTERVAL_SECONDS`
- [x] Auto-sync + polling: GET /latest → 404 → POST /sync → poll 3s → auto-refresh
- [x] Throughput = дельта: кол-во resolved с предыдущего снапшота
- [x] Read-only UI: браузер только читает GET /latest и GET /history
- [x] POST /sync → 202 queued (без метрик в ответе)
- [x] Flow Efficiency (5-я KPI, amber, формула: cycleTime/timeToMarket×100, кап 100%)
- [x] Lead Time → Time to Market (rename везде: server, JSON, HTML, тесты)
- [x] Throughput — убран period label из карточки
- [x] UX overhaul: KPI-акценты, collapsible sidebar, empty state, period bar
- [x] Автосинк при смене периода (только перезагружает историю, не KPI)
- [x] Восстановление connected-состояния при обновлении страницы
- [x] Jira pagination (PAGE_SIZE=50, cursor-based)
- [x] Changelog fetch для всех задач
- [x] Case-insensitive статусная модель
- [x] Smart Telegram chunking (split по \n / пробел / hard cut)
- [x] Regression suite: 108 тестов, stdlib unittest, zero deps
- [x] BUG-1: Done без resolutiondate корректно попадает в Throughput
- [x] BUG-2: Cycle Time от последнего старта перед done
- [x] BUG-3: Reopened фильтруется по периоду (только среди completed)
- [x] BUG-4: Задачи In Progress → Backlog видимы (changelog для всех)
- [x] BUG-5: Удалён дублирующий completedCount

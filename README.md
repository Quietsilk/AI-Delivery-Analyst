# AI Delivery Analyst

Базовый каркас проекта под MVP из ТЗ: сбор Jira-данных, расчёт delivery-метрик, AI-анализ и отправка отчёта.

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

1. Берёт задачи из Jira по `JIRA_JQL`.
2. Нормализует их в доменную модель `Issue`.
3. Считает базовые delivery metrics.
4. Отправляет delivery snapshot в OpenAI Responses API.
5. Формирует текстовый отчёт и публикует его в stdout.

## OpenAI Notes

- По умолчанию analysis-слой использует `Responses API`.
- Модель и reasoning effort задаются через `OPENAI_MODEL` и `OPENAI_REASONING_EFFORT`.
- Если `OPENAI_API_KEY` не задан, отчёт всё равно соберётся, но AI-анализ будет пропущен.

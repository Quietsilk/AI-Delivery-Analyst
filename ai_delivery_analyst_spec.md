# AI Delivery Analyst — Technical Specification (MVP)

## 1. Overview

AI Delivery Analyst — система автоматического анализа delivery-метрик на основе данных из Jira с использованием LLM.

Система:
- собирает данные из Jira
- считает ключевые метрики
- анализирует их через AI
- выявляет риски и узкие места
- отправляет actionable отчёт

---

## 2. Architecture

[Jira API] → [n8n Workflow] → [Transform Layer] → [LLM] → [Telegram/Slack]
                                      ↓
                                  [Storage]

---

## 3. Data Model

### Issue:
{
  "id": "JIRA-123",
  "type": "task|bug|story",
  "status": "To Do|In Progress|Done",
  "created_at": "timestamp",
  "started_at": "timestamp|null",
  "resolved_at": "timestamp|null",
  "assignee": "user",
  "estimate": 5,
  "story_points": 3,
  "reopened": true|false
}

---

## 4. Metrics Calculation

- Cycle Time = started_at → resolved_at
- Lead Time = created_at → resolved_at
- Throughput = tasks completed / period
- Predictability = completed / planned

---

## 5. n8n Workflow (MVP)

1. Cron Trigger (daily)
2. HTTP Request (Jira API)
3. Transform Node
4. Metrics Node
5. AI Node
6. Output Node (Telegram/Slack)

---

## 6. AI Prompt

You are a Senior Delivery Manager.

Analyze delivery metrics:
- Identify risks
- Explain causes
- Suggest actions

Rules:
- No generic advice
- Be concise
- Focus on delivery impact

---

## 7. Output Example

⚠️ Delivery Report

Predictability: 84% (-9%)
Cycle Time: 3.2d (+20%)

Risks:
- QA bottleneck
- Overcommitment

Actions:
- Reduce sprint scope
- Limit WIP

---

## 8. Definition of Done

- автоматический запуск
- корректные метрики
- осмысленный AI-анализ
- отправка отчета без участия


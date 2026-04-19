# Architecture Notes

MVP flow:

1. Scheduler triggers daily analysis.
2. Jira integration fetches issues for target scope.
3. Transform layer normalizes raw Jira fields to domain `Issue`.
4. Metrics layer calculates delivery KPIs.
5. AI layer interprets metrics and produces actionable recommendations.
6. Reporting layer sends the final summary to Telegram or Slack.

This repo currently contains a service-oriented skeleton. `n8n` can remain the main orchestrator, while this codebase acts as the execution layer for custom logic.

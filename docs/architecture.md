# Architecture Notes

MVP flow:

1. Scheduler triggers daily analysis.
2. Jira integration iterates over one or more configured delivery sources.
3. Each source carries its own project key, JQL, methodology (`scrum` or `kanban`), and status mapping.
4. Transform layer normalizes raw Jira fields to domain `Issue`.
5. Metrics layer calculates delivery KPIs per source and for the aggregate portfolio.
6. AI layer interprets metrics with awareness of source methodology and produces actionable recommendations.
7. Reporting layer sends the final summary to Telegram or Slack.

## Source Model

Each Jira source represents a delivery context rather than just a project.

- `kanban` sources emphasize flow metrics such as lead time, cycle time, and throughput.
- `kanban` sources also surface operational state such as backlog size and current WIP.
- `scrum` sources prepare the architecture for sprint-aware predictability and planned-versus-completed analysis.

## Current Metric Semantics

- Aggregate metrics summarize the full portfolio across all configured sources.
- Per-source metrics keep the methodology context visible in reporting and AI analysis.
- `predictability` is currently calculated as `completed / issues in source scope`.
- For `scrum`, Jira Agile API enrichment is used when an active sprint is available.
- If no active sprint exists yet, the system falls back to the scope-based proxy and reports that limitation explicitly.

## Simulation Layer

The project also includes a Jira simulation workflow for validation and demo purposes.

- `kanban` simulation creates a mixed flow of done, in-progress, and backlog work.
- `scrum` simulation creates a pseudo-sprint pattern with completed scope and spillover work.
- This allows validating metrics and delivery reporting without waiting for a real team cadence.

This repo currently contains a service-oriented skeleton. `n8n` can remain the main orchestrator, while this codebase acts as the execution layer for custom logic.

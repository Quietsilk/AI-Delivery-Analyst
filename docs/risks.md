# Risks

- Jira API token is temporary and currently expires on April 30, 2026. If it is not rotated before that date, live Jira ingestion and test runs will fail.
- The current integration assumes `In Progress` is the start status. If the project workflow changes or adds parallel in-progress states, `startedAt` may become inaccurate until `JIRA_STARTED_STATUSES` is updated.
- Story points exist in more than one field on this Jira instance (`customfield_10016` and `customfield_10038`). The project currently uses `customfield_10016`, so this should be revalidated if issue types or Jira configuration change.

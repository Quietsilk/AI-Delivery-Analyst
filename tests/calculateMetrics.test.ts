import test from "node:test";
import assert from "node:assert/strict";
import { calculateMetrics } from "../src/domain/metrics/calculateMetrics.js";
import { buildPrompt } from "../src/services/analysis/buildPrompt.js";
import { mapJiraIssue } from "../src/services/jira/mapIssue.js";

test("calculateMetrics returns zeroes for empty issues list", () => {
  const result = calculateMetrics([]);

  assert.equal(result.cycleTimeHours, 0);
  assert.equal(result.leadTimeHours, 0);
  assert.equal(result.throughput, 0);
  assert.equal(result.predictability, 0);
});

test("mapJiraIssue normalizes jira search issue into domain issue", () => {
  const result = mapJiraIssue(
    {
      id: "10001",
      key: "TEAM-1",
      fields: {
        issuetype: { name: "Story" },
        status: { name: "Done" },
        created: "2026-04-01T08:00:00.000Z",
        resolutiondate: "2026-04-03T10:00:00.000Z",
        assignee: { displayName: "Alex" },
        customfield_10016: 5,
        timeoriginalestimate: 28800
      },
      changelog: {
        histories: [
          {
            created: "2026-04-01T09:00:00.000Z",
            items: [{ field: "status", toString: "In Progress" }]
          },
          {
            created: "2026-04-03T12:00:00.000Z",
            items: [{ field: "status", fromString: "Done", toString: "In Progress" }]
          }
        ]
      }
    },
    {
      jiraBaseUrl: "https://example.atlassian.net",
      jiraEmail: "team@example.com",
      jiraApiToken: "token",
      jiraProjectKey: "TEAM",
      jiraJql: "project = TEAM",
      jiraStartedStatuses: ["In Progress"],
      jiraStoryPointsField: "customfield_10016",
      jiraOriginalEstimateField: "timeoriginalestimate",
      jiraPageSize: 50,
      openAiApiKey: "test",
      openAiBaseUrl: "https://api.openai.com/v1",
      openAiModel: "gpt-5-mini",
      openAiReasoningEffort: "medium",
      reportChannel: "telegram"
    }
  );

  assert.equal(result.id, "TEAM-1");
  assert.equal(result.type, "story");
  assert.equal(result.startedAt, "2026-04-01T09:00:00.000Z");
  assert.equal(result.storyPoints, 5);
  assert.equal(result.estimate, 28800);
  assert.equal(result.reopened, true);
});

test("buildPrompt includes issue context for AI analysis", () => {
  const prompt = buildPrompt(
    {
      cycleTimeHours: 12,
      leadTimeHours: 24,
      throughput: 3,
      predictability: 0.75
    },
    [
      {
        id: "TEAM-2",
        type: "bug",
        status: "In Progress",
        createdAt: "2026-04-01T08:00:00.000Z",
        startedAt: "2026-04-01T09:00:00.000Z",
        resolvedAt: null,
        assignee: "Sam",
        estimate: 14400,
        storyPoints: 3,
        reopened: false
      }
    ]
  );

  assert.match(prompt, /Issues in scope: 1/);
  assert.match(prompt, /TEAM-2: In Progress, assignee=Sam, type=bug/);
  assert.match(prompt, /Actions:/);
});

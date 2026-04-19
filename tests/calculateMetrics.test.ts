import test from "node:test";
import assert from "node:assert/strict";
import { loadConfig } from "../src/config/env.js";
import { calculateMetrics } from "../src/domain/metrics/calculateMetrics.js";
import { buildPrompt } from "../src/services/analysis/buildPrompt.js";
import { mapJiraIssue } from "../src/services/jira/mapIssue.js";

test("calculateMetrics returns zeroes for empty issues list", () => {
  const result = calculateMetrics([]);

  assert.equal(result.cycleTimeHours, 0);
  assert.equal(result.leadTimeHours, 0);
  assert.equal(result.throughput, 0);
  assert.equal(result.predictability, 0);
  assert.equal(result.backlogSize, 0);
  assert.equal(result.inProgressCount, 0);
  assert.equal(result.completedCount, 0);
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
      jiraSources: [
        {
          key: "team",
          projectKey: "TEAM",
          methodology: "kanban",
          jql: "project = TEAM",
          startedStatuses: ["In Progress"]
        }
      ],
      jiraStoryPointsField: "customfield_10016",
      jiraOriginalEstimateField: "timeoriginalestimate",
      jiraPageSize: 50,
      openAiApiKey: "test",
      openAiBaseUrl: "https://api.openai.com/v1",
      openAiModel: "gpt-5-mini",
      openAiReasoningEffort: "medium",
      reportChannel: "telegram",
      telegramBotToken: "test-token",
      telegramChatId: "123456",
      slackWebhookUrl: ""
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
        predictability: 0.75,
        backlogSize: 2,
        inProgressCount: 1,
        completedCount: 3
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
    ],
    [
      {
        sourceKey: "kanban",
        projectKey: "KAN",
        methodology: "kanban",
        metrics: {
          cycleTimeHours: 12,
          leadTimeHours: 24,
          throughput: 3,
          predictability: 0.75,
          backlogSize: 2,
          inProgressCount: 1,
          completedCount: 3
        },
        issues: [
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
        ],
        scrumInsight: null
      }
    ]
  );

  assert.match(prompt, /Issues in scope: 1/);
  assert.match(prompt, /Backlog size: 2/);
  assert.match(prompt, /TEAM-2: In Progress, assignee=Sam, type=bug/);
  assert.match(prompt, /kanban: methodology=kanban, project=KAN/);
  assert.match(prompt, /Actions:/);
});

test("loadConfig parses multiple jira delivery sources", () => {
  process.env.JIRA_PROJECT_KEY = "TEST";
  process.env.JIRA_JQL = "project = \"TEST\" ORDER BY updated DESC";
  process.env.JIRA_STARTED_STATUSES = "In Progress";
  process.env.JIRA_SOURCES =
    "kanban|kanban|KAN|project = \"KAN\" ORDER BY updated DESC|In Progress;scrum|scrum|SCRUM|project = \"SCRUM\" ORDER BY updated DESC|In Progress,Selected for Development";

  const config = loadConfig();

  assert.equal(config.jiraSources.length, 2);
  assert.deepEqual(config.jiraSources[0], {
    key: "kanban",
    methodology: "kanban",
    projectKey: "KAN",
    jql: "project = \"KAN\" ORDER BY updated DESC",
    startedStatuses: ["In Progress"]
  });
  assert.deepEqual(config.jiraSources[1], {
    key: "scrum",
    methodology: "scrum",
    projectKey: "SCRUM",
    jql: "project = \"SCRUM\" ORDER BY updated DESC",
    startedStatuses: ["In Progress", "Selected for Development"]
  });
});

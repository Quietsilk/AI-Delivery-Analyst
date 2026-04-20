import test from "node:test";
import assert from "node:assert/strict";
import { AppConfig, JiraSourceConfig } from "../src/config/env.js";
import { fetchScrumSprintInsight } from "../src/services/jira/agileInsights.js";

const baseConfig: AppConfig = {
  jiraBaseUrl: "https://example.atlassian.net",
  jiraEmail: "team@example.com",
  jiraApiToken: "token",
  jiraProjectKey: "SCR",
  jiraJql: "project = SCR",
  jiraStartedStatuses: ["In Progress"],
  jiraSources: [],
  jiraStoryPointsField: "customfield_10016",
  jiraOriginalEstimateField: "timeoriginalestimate",
  jiraPageSize: 50,
  openAiApiKey: "",
  openAiBaseUrl: "https://api.openai.com/v1",
  openAiModel: "gpt-5-mini",
  openAiReasoningEffort: "medium",
  reportChannel: "telegram",
  telegramBotToken: "",
  telegramChatId: "",
  slackWebhookUrl: ""
};

const scrumSource: JiraSourceConfig = {
  key: "scrum",
  projectKey: "SCR",
  methodology: "scrum",
  jql: "project = SCR",
  startedStatuses: ["In Progress"]
};

function jsonResponse(payload: unknown): Response {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: {
      "Content-Type": "application/json"
    }
  });
}

test("fetchScrumSprintInsight paginates sprint issues and counts done-like statuses", async (t) => {
  const originalFetch = globalThis.fetch;

  t.after(() => {
    globalThis.fetch = originalFetch;
  });

  globalThis.fetch = (async (input: string | URL | Request): Promise<Response> => {
    const url = new URL(typeof input === "string" ? input : input.url);

    if (url.pathname === "/rest/agile/1.0/board") {
      return jsonResponse({
        values: [
          {
            id: 1,
            name: "SCR Board",
            type: "scrum",
            location: { projectKey: "SCR" }
          }
        ]
      });
    }

    if (url.pathname === "/rest/agile/1.0/board/1/sprint") {
      return jsonResponse({
        values: [
          { id: 42, name: "Sprint 42", state: "active" }
        ]
      });
    }

    if (url.pathname === "/rest/agile/1.0/board/1/sprint/42/issue") {
      const startAt = Number(url.searchParams.get("startAt") ?? "0");

      if (startAt === 0) {
        const issues = Array.from({ length: 100 }, (_, index) => ({
          key: `SCR-${index + 1}`,
          fields: {
            resolutiondate: index < 50 ? "2026-04-20T10:00:00.000Z" : null,
            status: { name: "In Progress" }
          }
        }));

        return jsonResponse({
          issues,
          total: 101
        });
      }

      return jsonResponse({
        issues: [
          {
            key: "SCR-101",
            fields: {
              resolutiondate: null,
              status: { name: "Closed" }
            }
          }
        ],
        total: 101
      });
    }

    throw new Error(`Unexpected fetch URL: ${url.toString()}`);
  }) as typeof fetch;

  const insight = await fetchScrumSprintInsight(baseConfig, scrumSource, []);

  assert.ok(insight);
  assert.equal(insight?.activeSprintId, 42);
  assert.equal(insight?.committedIssues, 101);
  assert.equal(insight?.completedCommittedIssues, 51);
  assert.equal(insight?.predictabilityFromSprint, 51 / 101);
});

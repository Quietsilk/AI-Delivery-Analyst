import { loadConfig } from "../config/env.js";
import { loadDotEnv } from "../config/loadDotEnv.js";

interface JiraSearchResponse {
  issues?: Array<{
    key: string;
    fields: Record<string, unknown>;
    changelog?: {
      histories?: Array<{
        created: string;
        items: Array<{
          field: string;
          fromString?: string | null;
          toString?: string | null;
        }>;
      }>;
    };
  }>;
}

async function main(): Promise<void> {
  loadDotEnv();
  const config = loadConfig();
  const requestedSourceKey = process.argv[2];
  const sources = requestedSourceKey
    ? config.jiraSources.filter((source) => source.key === requestedSourceKey)
    : config.jiraSources;

  assertRequired(config.jiraBaseUrl, "JIRA_BASE_URL");
  assertRequired(config.jiraEmail, "JIRA_EMAIL");
  assertRequired(config.jiraApiToken, "JIRA_API_TOKEN");
  if (sources.length === 0) {
    throw new Error(`No Jira source matched the requested key: ${requestedSourceKey}`);
  }

  for (const source of sources) {
    const url = new URL("/rest/api/3/search/jql", config.jiraBaseUrl);
    url.searchParams.set("jql", source.jql);
    url.searchParams.set("startAt", "0");
    url.searchParams.set("maxResults", "3");
    url.searchParams.set("fields", "*all");
    url.searchParams.set("expand", "changelog");

    const response = await fetch(url, {
      method: "GET",
      headers: {
        "Accept": "application/json",
        "Authorization": `Basic ${Buffer.from(
          `${config.jiraEmail}:${config.jiraApiToken}`
        ).toString("base64")}`
      }
    });

    if (!response.ok) {
      const body = await response.text();
      throw new Error(
        `Jira inspect failed for source ${source.key} with status ${response.status}: ${body.slice(0, 1000)}`
      );
    }

    const payload = (await response.json()) as JiraSearchResponse;
    const issues = payload.issues ?? [];

    console.log("");
    console.log(
      `Source ${source.key} (${source.methodology}, project=${source.projectKey}) fetched ${issues.length} issues for inspection.`
    );

    for (const issue of issues) {
      const fieldKeys = Object.keys(issue.fields).sort();
      const statusTransitions =
        issue.changelog?.histories
          ?.flatMap((history) =>
            history.items
              .filter((item) => item.field.toLowerCase() === "status")
              .map(
                (item) =>
                  `${history.created}: ${item.fromString ?? "null"} -> ${item.toString ?? "null"}`
              )
          )
          .slice(0, 10) ?? [];

      console.log("");
      console.log(`Issue: ${issue.key}`);
      console.log(`Field keys (${fieldKeys.length}): ${fieldKeys.join(", ")}`);
      console.log(
        `Known candidate values: ${JSON.stringify(
          {
            status: getNestedString(issue.fields, ["status", "name"]),
            issueType: getNestedString(issue.fields, ["issuetype", "name"]),
            assignee: getNestedString(issue.fields, ["assignee", "displayName"]),
            created: getString(issue.fields.created),
            resolutiondate: getString(issue.fields.resolutiondate),
            statuscategorychangedate: getString(issue.fields.statuscategorychangedate),
            timeoriginalestimate: issue.fields.timeoriginalestimate,
            customfield_10016: issue.fields.customfield_10016,
            customfield_10038: issue.fields.customfield_10038
          },
          null,
          2
        )}`
      );
      console.log(
        `Status transitions: ${
          statusTransitions.length > 0 ? statusTransitions.join(" | ") : "none"
        }`
      );
    }
  }
}

function assertRequired(value: string, name: string): void {
  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`);
  }
}

function getString(value: unknown): string | null {
  return typeof value === "string" ? value : null;
}

function getNestedString(
  value: Record<string, unknown>,
  path: string[]
): string | null {
  let current: unknown = value;

  for (const key of path) {
    if (!current || typeof current !== "object" || !(key in current)) {
      return null;
    }

    current = (current as Record<string, unknown>)[key];
  }

  return typeof current === "string" ? current : null;
}

main().catch((error) => {
  console.error("Jira inspection failed.", error);
  process.exitCode = 1;
});

import { AppConfig } from "../../config/env.js";
import { Issue } from "../../domain/entities/Issue.js";
import { mapJiraIssue } from "./mapIssue.js";
import { JiraSearchResponse } from "./types.js";

export class JiraClient {
  constructor(private readonly config: AppConfig) {}

  async fetchIssues(): Promise<Issue[]> {
    const rawIssues = await this.fetchAllIssues();

    return rawIssues.map((issue) => mapJiraIssue(issue, this.config));
  }

  private async fetchAllIssues(): Promise<JiraSearchResponse["issues"]> {
    const issues: JiraSearchResponse["issues"] = [];
    let startAt = 0;

    while (true) {
      const page = await this.fetchIssuesPage(startAt);
      issues.push(...page.issues);
      startAt += page.issues.length;

      if (page.isLast === true || page.issues.length === 0) {
        break;
      }
    }

    return issues;
  }

  private async fetchIssuesPage(startAt: number): Promise<JiraSearchResponse> {
    const url = new URL("/rest/api/3/search/jql", this.config.jiraBaseUrl);
    url.searchParams.set("jql", this.config.jiraJql);
    url.searchParams.set("startAt", String(startAt));
    url.searchParams.set("maxResults", String(this.config.jiraPageSize));
    url.searchParams.set(
      "fields",
      [
        "summary",
        "issuetype",
        "status",
        "assignee",
        "created",
        "resolutiondate",
        "statuscategorychangedate",
        "timeoriginalestimate",
        this.config.jiraOriginalEstimateField,
        this.config.jiraStoryPointsField
      ].join(",")
    );
    url.searchParams.set("expand", "changelog");

    const response = await fetch(url, {
      method: "GET",
      headers: {
        "Accept": "application/json",
        "Authorization": `Basic ${this.getBasicAuthToken()}`
      }
    });

    if (!response.ok) {
      const body = await response.text();
      throw new Error(
        `Jira search failed with status ${response.status}: ${body.slice(0, 500)}`
      );
    }

    return (await response.json()) as JiraSearchResponse;
  }

  private getBasicAuthToken(): string {
    return Buffer.from(
      `${this.config.jiraEmail}:${this.config.jiraApiToken}`
    ).toString("base64");
  }
}

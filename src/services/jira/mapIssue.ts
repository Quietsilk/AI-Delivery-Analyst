import { AppConfig } from "../../config/env.js";
import { Issue } from "../../domain/entities/Issue.js";
import { JiraHistory, JiraIssue } from "./types.js";

const DEFAULT_ISSUE_TYPE: Issue["type"] = "task";

export function mapJiraIssue(issue: JiraIssue, config: AppConfig): Issue {
  const fields = issue.fields;
  const changelog = issue.changelog?.histories ?? [];
  const status = getNestedString(fields, ["status", "name"]) ?? "Unknown";

  return {
    id: issue.key || issue.id,
    type: mapIssueType(getNestedString(fields, ["issuetype", "name"])),
    status,
    createdAt: getStringField(fields["created"]) ?? new Date(0).toISOString(),
    startedAt: detectStartedAt(changelog, config.jiraStartedStatuses),
    resolvedAt: detectResolvedAt(fields, changelog),
    assignee: getNestedString(fields, ["assignee", "displayName"]),
    estimate: getNumberField(fields[config.jiraOriginalEstimateField]),
    storyPoints: getNumberField(fields[config.jiraStoryPointsField]),
    reopened: detectReopened(changelog)
  };
}

function mapIssueType(rawType: string | null): Issue["type"] {
  if (!rawType) {
    return DEFAULT_ISSUE_TYPE;
  }

  const normalized = rawType.trim().toLowerCase();

  if (normalized === "bug") {
    return "bug";
  }

  if (normalized === "story") {
    return "story";
  }

  return "task";
}

function detectStartedAt(
  histories: JiraHistory[],
  startedStatuses: string[]
): string | null {
  const allowedStatuses = new Set(startedStatuses.map((status) => status.toLowerCase()));

  const startedTransition = histories
    .slice()
    .sort((left, right) => Date.parse(left.created) - Date.parse(right.created))
    .find((history) =>
      history.items.some((item) => {
        if (item.field.toLowerCase() !== "status") {
          return false;
        }

        return allowedStatuses.has((item.toString ?? "").toLowerCase());
      })
    );

  return startedTransition?.created ?? null;
}

function detectReopened(histories: JiraHistory[]): boolean {
  let seenDoneStatus = false;

  const sorted = histories
    .slice()
    .sort((left, right) => Date.parse(left.created) - Date.parse(right.created));

  for (const history of sorted) {
    for (const item of history.items) {
      if (item.field.toLowerCase() !== "status") {
        continue;
      }

      const fromStatus = (item.fromString ?? "").toLowerCase();
      const toStatus = (item.toString ?? "").toLowerCase();

      if (isDoneLikeStatus(fromStatus) || isDoneLikeStatus(toStatus)) {
        seenDoneStatus = true;
      }

      if (seenDoneStatus && !isDoneLikeStatus(toStatus) && toStatus.length > 0) {
        return true;
      }

      if (toStatus === "reopened") {
        return true;
      }
    }
  }

  return false;
}

function detectResolvedAt(
  fields: Record<string, unknown>,
  histories: JiraHistory[]
): string | null {
  const resolutionDate = getStringField(fields["resolutiondate"]);

  if (resolutionDate) {
    return resolutionDate;
  }

  const doneTransition = histories
    .slice()
    .sort((left, right) => Date.parse(left.created) - Date.parse(right.created))
    .find((history) =>
      history.items.some((item) => {
        if (item.field.toLowerCase() !== "status") {
          return false;
        }

        return isDoneLikeStatus((item.toString ?? "").toLowerCase());
      })
    );

  return doneTransition?.created ?? null;
}

function isDoneLikeStatus(status: string): boolean {
  return ["done", "closed", "resolved"].includes(status);
}

function getStringField(value: unknown): string | null {
  return typeof value === "string" && value.length > 0 ? value : null;
}

function getNumberField(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }

  if (typeof value === "string" && value.length > 0) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }

  return null;
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

  return typeof current === "string" && current.length > 0 ? current : null;
}

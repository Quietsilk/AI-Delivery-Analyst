import { Issue } from "../entities/Issue.js";
import { DeliveryMetrics } from "./types.js";
import { averageHoursBetween } from "../../utils/date.js";

export function calculateMetrics(issues: Issue[]): DeliveryMetrics {
  const completedIssues = issues.filter((issue) => issue.resolvedAt);

  return {
    cycleTimeHours: averageHoursBetween(
      completedIssues.map((issue) => ({
        start: issue.startedAt,
        end: issue.resolvedAt
      }))
    ),
    leadTimeHours: averageHoursBetween(
      completedIssues.map((issue) => ({
        start: issue.createdAt,
        end: issue.resolvedAt
      }))
    ),
    throughput: completedIssues.length,
    predictability: issues.length === 0 ? 0 : completedIssues.length / issues.length
  };
}

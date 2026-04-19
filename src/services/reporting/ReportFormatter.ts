import { SourceMetrics } from "../../domain/metrics/SourceMetrics.js";
import { DeliveryMetrics } from "../../domain/metrics/types.js";
import { Issue } from "../../domain/entities/Issue.js";
import { formatSourceSummary } from "./formatSourceSummary.js";

export function formatReport(
  metrics: DeliveryMetrics,
  analysis: string,
  issues: Issue[],
  sources: SourceMetrics[]
): string {
  const completedIssues = issues.filter((issue) => issue.resolvedAt);
  const reopenedIssues = issues.filter((issue) => issue.reopened);

  return [
    "Delivery Report",
    "",
    `Issues in scope: ${issues.length}`,
    `Completed issues: ${completedIssues.length}`,
    `Reopened issues: ${reopenedIssues.length}`,
    `Backlog size: ${metrics.backlogSize}`,
    `In Progress count: ${metrics.inProgressCount}`,
    `Cycle Time: ${metrics.cycleTimeHours.toFixed(2)}h`,
    `Lead Time: ${metrics.leadTimeHours.toFixed(2)}h`,
    `Throughput: ${metrics.throughput}`,
    `Predictability: ${(metrics.predictability * 100).toFixed(1)}%`,
    "",
    "Source breakdown",
    "",
    ...sources.map((source) => formatSourceSummary(source)),
    "",
    analysis
  ].join("\n");
}

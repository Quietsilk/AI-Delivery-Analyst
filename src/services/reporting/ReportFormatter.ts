import { DeliveryMetrics } from "../../domain/metrics/types.js";
import { Issue } from "../../domain/entities/Issue.js";

export function formatReport(
  metrics: DeliveryMetrics,
  analysis: string,
  issues: Issue[]
): string {
  const completedIssues = issues.filter((issue) => issue.resolvedAt);
  const reopenedIssues = issues.filter((issue) => issue.reopened);

  return [
    "Delivery Report",
    "",
    `Issues in scope: ${issues.length}`,
    `Completed issues: ${completedIssues.length}`,
    `Reopened issues: ${reopenedIssues.length}`,
    `Cycle Time: ${metrics.cycleTimeHours.toFixed(2)}h`,
    `Lead Time: ${metrics.leadTimeHours.toFixed(2)}h`,
    `Throughput: ${metrics.throughput}`,
    `Predictability: ${(metrics.predictability * 100).toFixed(1)}%`,
    "",
    analysis
  ].join("\n");
}

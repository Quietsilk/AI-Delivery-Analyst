import { SourceMetrics } from "../../domain/metrics/SourceMetrics.js";
import { formatMethodologyNote } from "./formatMethodologyNote.js";

export function formatSourceSummary(source: SourceMetrics): string {
  const completedIssues = source.issues.filter((issue) => issue.resolvedAt);
  const reopenedIssues = source.issues.filter((issue) => issue.reopened);

  return [
    `[${source.sourceKey}] ${source.projectKey} (${source.methodology})`,
    `Issues in scope: ${source.issues.length}`,
    `Completed issues: ${completedIssues.length}`,
    `Reopened issues: ${reopenedIssues.length}`,
    `Backlog size: ${source.metrics.backlogSize}`,
    `In Progress count: ${source.metrics.inProgressCount}`,
    `Cycle Time: ${source.metrics.cycleTimeHours.toFixed(2)}h`,
    `Lead Time: ${source.metrics.leadTimeHours.toFixed(2)}h`,
    `Throughput: ${source.metrics.throughput}`,
    `Predictability: ${(source.metrics.predictability * 100).toFixed(1)}%`,
    formatMethodologyNote(source)
  ].join("\n");
}

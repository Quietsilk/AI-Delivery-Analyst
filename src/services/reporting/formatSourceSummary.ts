import { SourceMetrics } from "../../domain/metrics/SourceMetrics.js";

export function formatSourceSummary(source: SourceMetrics): string {
  const reopenedIssues = source.issues.filter((issue) => issue.reopened);
  const methodology = source.methodology === "scrum" ? "Scrum" : "Kanban";
  const predictabilityIcon =
    source.metrics.predictability >= 0.8 ? "🟢" : source.metrics.predictability >= 0.6 ? "🟡" : "🔴";

  const lines: string[] = [];

  // Header
  const sprintLabel =
    source.methodology === "scrum" && source.scrumInsight?.activeSprintName
      ? ` · ${source.scrumInsight.activeSprintName}`
      : "";
  lines.push(`▸ ${source.projectKey} · ${methodology}${sprintLabel}`);

  // Issue counts
  const reopenedPart = reopenedIssues.length > 0 ? `   ⚠️ Reopened: ${reopenedIssues.length}` : "";
  lines.push(
    `  ✅ ${source.metrics.completedCount} done   🔄 ${source.metrics.inProgressCount} in progress   📋 ${source.metrics.backlogSize} backlog${reopenedPart}`
  );

  // Predictability
  if (source.methodology === "scrum" && source.scrumInsight?.activeSprintId) {
    const committed = source.scrumInsight.committedIssues ?? 0;
    const completed = source.scrumInsight.completedCommittedIssues ?? 0;
    const pct = ((source.scrumInsight.predictabilityFromSprint ?? 0) * 100).toFixed(0);
    lines.push(`  ${predictabilityIcon} Sprint predictability: ${pct}% (${completed}/${committed} committed)`);
  } else {
    lines.push(
      `  ${predictabilityIcon} Predictability: ${(source.metrics.predictability * 100).toFixed(0)}%`
    );
  }

  // Metrics
  lines.push(
    `  ⏱ CT: ${formatHours(source.metrics.cycleTimeHours)}   📅 LT: ${formatHours(source.metrics.leadTimeHours)}   🚀 TP: ${source.metrics.throughput}`
  );

  return lines.join("\n");
}

function formatHours(hours: number): string {
  if (hours === 0) return "—";
  if (hours < 24) return `${hours.toFixed(0)}h`;
  const days = hours / 24;
  return `${days.toFixed(1)}d`;
}

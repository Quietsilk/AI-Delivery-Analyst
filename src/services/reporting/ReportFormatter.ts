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
  const reopenedIssues = issues.filter((issue) => issue.reopened);
  const date = new Date().toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric"
  });

  const predictabilityIcon = metrics.predictability >= 0.8 ? "🟢" : metrics.predictability >= 0.6 ? "🟡" : "🔴";

  const sections: string[] = [
    `📊 Delivery Report — ${date}`,
    "",
    "━━━ Overview ━━━",
    `✅ Completed: ${metrics.completedCount}   🔄 In Progress: ${metrics.inProgressCount}   📋 Backlog: ${metrics.backlogSize}`,
    reopenedIssues.length > 0
      ? `⚠️ Reopened: ${reopenedIssues.length}   ${predictabilityIcon} Predictability: ${(metrics.predictability * 100).toFixed(0)}%`
      : `${predictabilityIcon} Predictability: ${(metrics.predictability * 100).toFixed(0)}%`,
    `⏱ Cycle Time: ${formatHours(metrics.cycleTimeHours)}   📅 Lead Time: ${formatHours(metrics.leadTimeHours)}   🚀 Throughput: ${metrics.throughput}`,
  ];

  if (sources.length > 1) {
    sections.push("");
    sections.push("━━━ Sources ━━━");
    for (const source of sources) {
      sections.push("");
      sections.push(formatSourceSummary(source));
    }
  }

  sections.push("");
  sections.push("━━━ AI Analysis ━━━");
  sections.push(analysis);

  return sections.join("\n");
}

function formatHours(hours: number): string {
  if (hours === 0) return "—";
  if (hours < 24) return `${hours.toFixed(0)}h`;
  const days = hours / 24;
  return `${days.toFixed(1)}d`;
}

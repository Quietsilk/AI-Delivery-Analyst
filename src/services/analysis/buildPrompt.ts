import { DeliveryMetrics } from "../../domain/metrics/types.js";
import { Issue } from "../../domain/entities/Issue.js";

export function buildPrompt(metrics: DeliveryMetrics, issues: Issue[]): string {
  const reopenedIssues = issues.filter((issue) => issue.reopened);
  const topOpenIssues = issues
    .filter((issue) => !issue.resolvedAt)
    .slice(0, 5)
    .map(
      (issue) =>
        `- ${issue.id}: ${issue.status}, assignee=${issue.assignee ?? "unassigned"}, type=${issue.type}`
    );

  return [
    "You are a Senior Delivery Manager preparing a short actionable delivery report.",
    "",
    "Analyze the following delivery snapshot:",
    `- Issues in scope: ${issues.length}`,
    `- Reopened issues: ${reopenedIssues.length}`,
    `- Cycle Time (hours): ${metrics.cycleTimeHours.toFixed(2)}`,
    `- Lead Time (hours): ${metrics.leadTimeHours.toFixed(2)}`,
    `- Throughput: ${metrics.throughput}`,
    `- Predictability: ${metrics.predictability.toFixed(2)}`,
    "",
    "Open issues sample:",
    ...(topOpenIssues.length > 0 ? topOpenIssues : ["- none"]),
    "",
    "Rules:",
    "- Identify risks",
    "- Explain causes",
    "- Suggest actions",
    "- No generic advice",
    "- Be concise",
    "- Focus on delivery impact",
    "",
    "Return format:",
    "Summary: 1-2 sentences",
    "Risks:",
    "- bullet",
    "Actions:",
    "- bullet"
  ].join("\n");
}

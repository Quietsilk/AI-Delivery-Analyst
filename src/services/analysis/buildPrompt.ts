import { SourceMetrics } from "../../domain/metrics/SourceMetrics.js";
import { DeliveryMetrics } from "../../domain/metrics/types.js";
import { Issue } from "../../domain/entities/Issue.js";

export function buildPrompt(
  metrics: DeliveryMetrics,
  issues: Issue[],
  sources: SourceMetrics[]
): string {
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
    `- Backlog size: ${metrics.backlogSize}`,
    `- In Progress count: ${metrics.inProgressCount}`,
    `- Cycle Time (hours): ${metrics.cycleTimeHours.toFixed(2)}`,
    `- Lead Time (hours): ${metrics.leadTimeHours.toFixed(2)}`,
    `- Throughput: ${metrics.throughput}`,
    `- Predictability: ${metrics.predictability.toFixed(2)}`,
    "",
    "Delivery contexts:",
    ...sources.map(
      (source) =>
        `- ${source.sourceKey}: methodology=${source.methodology}, project=${source.projectKey}, throughput=${source.metrics.throughput}, predictability=${source.metrics.predictability.toFixed(2)}${
          source.scrumInsight?.activeSprintName
            ? `, activeSprint=${source.scrumInsight.activeSprintName}, sprintPredictability=${(source.scrumInsight.predictabilityFromSprint ?? 0).toFixed(2)}`
            : source.methodology === "scrum" && source.scrumInsight
              ? `, activeSprint=none, futureSprints=${source.scrumInsight.futureSprintCount}`
              : ""
        }`
    ),
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
    "- Account for methodology differences between scrum and kanban sources",
    "",
    "Return format:",
    "Summary: 1-2 sentences",
    "Risks:",
    "- bullet",
    "Actions:",
    "- bullet"
  ].join("\n");
}

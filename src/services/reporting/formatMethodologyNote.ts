import { SourceMetrics } from "../../domain/metrics/SourceMetrics.js";

export function formatMethodologyNote(source: SourceMetrics): string {
  if (source.methodology === "kanban") {
    return [
      "Methodology note:",
      `Kanban context emphasizes flow health. Current WIP=${source.metrics.inProgressCount}, backlog=${source.metrics.backlogSize}, throughput=${source.metrics.throughput}.`
    ].join("\n");
  }

  if (!source.scrumInsight) {
    return [
      "Methodology note:",
      "Scrum context is enabled in the architecture.",
      `Current predictability is a scope-based proxy (${(source.metrics.predictability * 100).toFixed(1)}% = completed / issues in source scope).`,
      "Agile board enrichment is unavailable for this source, so sprint-aware predictability could not be calculated."
    ].join("\n");
  }

  if (!source.scrumInsight.activeSprintId) {
    return [
      "Methodology note:",
      `Scrum board detected: ${source.scrumInsight.boardName} (#${source.scrumInsight.boardId}).`,
      `No active sprint is currently available. Future sprints detected: ${source.scrumInsight.futureSprintCount}.`,
      `Current predictability remains a scope-based proxy (${(source.metrics.predictability * 100).toFixed(1)}%) until a sprint is started and issues are committed to it.`
    ].join("\n");
  }

  return [
    "Methodology note:",
    `Scrum board detected: ${source.scrumInsight.boardName} (#${source.scrumInsight.boardId}), active sprint: ${source.scrumInsight.activeSprintName}.`,
    `Sprint-aware predictability: ${((source.scrumInsight.predictabilityFromSprint ?? 0) * 100).toFixed(1)}% (${source.scrumInsight.completedCommittedIssues}/${source.scrumInsight.committedIssues} committed issues completed).`,
    "Source-level predictability in the report is now backed by active sprint commitment rather than raw scope size."
  ].join("\n");
}

/**
 * Dry-run: прогоняет весь пайплайн на mock-данных без сетевых запросов.
 * Показывает метрики, prompt и финальный отчёт — без вызова OpenAI и Jira.
 *
 * Запуск: node --loader ts-node/esm src/scripts/dryRun.ts
 */

import { Issue } from "../domain/entities/Issue.js";
import { SourceMetrics } from "../domain/metrics/SourceMetrics.js";
import { calculateMetrics } from "../domain/metrics/calculateMetrics.js";
import { buildPrompt } from "../services/analysis/buildPrompt.js";
import { formatReport } from "../services/reporting/ReportFormatter.js";

// --- Mock данные ---

const now = new Date();
const daysAgo = (n: number) => new Date(now.getTime() - n * 24 * 60 * 60 * 1000).toISOString();

const kanbanIssues: Issue[] = [
  {
    id: "KAN-1", type: "task", status: "Done",
    createdAt: daysAgo(12), startedAt: daysAgo(8), resolvedAt: daysAgo(5),
    assignee: "alice", estimate: 3, storyPoints: 3, reopened: false
  },
  {
    id: "KAN-2", type: "bug", status: "Done",
    createdAt: daysAgo(10), startedAt: daysAgo(7), resolvedAt: daysAgo(3),
    assignee: "bob", estimate: 2, storyPoints: 2, reopened: true
  },
  {
    id: "KAN-3", type: "story", status: "Done",
    createdAt: daysAgo(14), startedAt: daysAgo(10), resolvedAt: daysAgo(1),
    assignee: "alice", estimate: 5, storyPoints: 5, reopened: false
  },
  {
    id: "KAN-4", type: "task", status: "In Progress",
    createdAt: daysAgo(6), startedAt: daysAgo(3), resolvedAt: null,
    assignee: "carol", estimate: 5, storyPoints: 5, reopened: false
  },
  {
    id: "KAN-5", type: "task", status: "In Progress",
    createdAt: daysAgo(8), startedAt: daysAgo(6), resolvedAt: null,
    assignee: "bob", estimate: 3, storyPoints: null, reopened: false
  },
  {
    id: "KAN-6", type: "bug", status: "To Do",
    createdAt: daysAgo(2), startedAt: null, resolvedAt: null,
    assignee: null, estimate: null, storyPoints: null, reopened: false
  },
  {
    id: "KAN-7", type: "task", status: "To Do",
    createdAt: daysAgo(1), startedAt: null, resolvedAt: null,
    assignee: null, estimate: 2, storyPoints: 2, reopened: false
  },
];

const scrumIssues: Issue[] = [
  {
    id: "SCR-1", type: "story", status: "Done",
    createdAt: daysAgo(20), startedAt: daysAgo(14), resolvedAt: daysAgo(7),
    assignee: "dave", estimate: 8, storyPoints: 8, reopened: false
  },
  {
    id: "SCR-2", type: "task", status: "Done",
    createdAt: daysAgo(18), startedAt: daysAgo(13), resolvedAt: daysAgo(6),
    assignee: "eve", estimate: 5, storyPoints: 5, reopened: false
  },
  {
    id: "SCR-3", type: "bug", status: "Done",
    createdAt: daysAgo(15), startedAt: daysAgo(12), resolvedAt: daysAgo(8),
    assignee: "dave", estimate: 3, storyPoints: 3, reopened: true
  },
  {
    id: "SCR-4", type: "story", status: "In Progress",
    createdAt: daysAgo(10), startedAt: daysAgo(5), resolvedAt: null,
    assignee: "frank", estimate: 13, storyPoints: 13, reopened: false
  },
  {
    id: "SCR-5", type: "task", status: "To Do",
    createdAt: daysAgo(5), startedAt: null, resolvedAt: null,
    assignee: null, estimate: 5, storyPoints: 5, reopened: false
  },
  {
    id: "SCR-6", type: "task", status: "To Do",
    createdAt: daysAgo(3), startedAt: null, resolvedAt: null,
    assignee: null, estimate: 3, storyPoints: 3, reopened: false
  },
];

// --- Metrics ---

const kanbanMetrics = calculateMetrics(kanbanIssues);
const scrumMetrics = calculateMetrics(scrumIssues);

const sources: SourceMetrics[] = [
  {
    sourceKey: "kanban",
    projectKey: "KAN",
    methodology: "kanban",
    metrics: kanbanMetrics,
    issues: kanbanIssues,
    scrumInsight: null,
  },
  {
    sourceKey: "scrum",
    projectKey: "SCR",
    methodology: "scrum",
    metrics: scrumMetrics,
    issues: scrumIssues,
    scrumInsight: {
      boardId: 1,
      boardName: "SCR Board",
      activeSprintId: 42,
      activeSprintName: "Sprint 7",
      futureSprintCount: 2,
      committedIssues: 6,
      completedCommittedIssues: 3,
      predictabilityFromSprint: 0.5,
    },
  },
];

const allIssues = [...kanbanIssues, ...scrumIssues];
const aggregateMetrics = calculateMetrics(allIssues);

// --- Output ---

const separator = "=".repeat(60);

console.log(separator);
console.log("AGGREGATE METRICS");
console.log(separator);
console.log(`Issues in scope:  ${allIssues.length}`);
console.log(`Completed:        ${aggregateMetrics.completedCount}`);
console.log(`In Progress:      ${aggregateMetrics.inProgressCount}`);
console.log(`Backlog:          ${aggregateMetrics.backlogSize}`);
console.log(`Cycle Time:       ${aggregateMetrics.cycleTimeHours.toFixed(2)}h`);
console.log(`Lead Time:        ${aggregateMetrics.leadTimeHours.toFixed(2)}h`);
console.log(`Throughput:       ${aggregateMetrics.throughput}`);
console.log(`Predictability:   ${(aggregateMetrics.predictability * 100).toFixed(1)}%`);

console.log("\n" + separator);
console.log("PROMPT (что улетит в OpenAI)");
console.log(separator);
console.log(buildPrompt(aggregateMetrics, allIssues, sources));

console.log("\n" + separator);
console.log("REPORT (что получит пользователь, без AI)");
console.log(separator);
const mockAnalysis = "[AI analysis skipped — OPENAI_API_KEY not set]";
console.log(formatReport(aggregateMetrics, mockAnalysis, allIssues, sources));

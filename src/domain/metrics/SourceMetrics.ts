import { Issue } from "../entities/Issue.js";
import { DeliveryMetrics } from "./types.js";
import { DeliveryMethodology } from "../../config/env.js";

export interface ScrumSprintInsight {
  boardId: number;
  boardName: string;
  activeSprintId: number | null;
  activeSprintName: string | null;
  futureSprintCount: number;
  committedIssues: number | null;
  completedCommittedIssues: number | null;
  predictabilityFromSprint: number | null;
}

export interface SourceMetrics {
  sourceKey: string;
  projectKey: string;
  methodology: DeliveryMethodology;
  metrics: DeliveryMetrics;
  issues: Issue[];
  scrumInsight?: ScrumSprintInsight | null;
}

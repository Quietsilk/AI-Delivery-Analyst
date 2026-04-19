import { AppConfig, JiraSourceConfig } from "../../config/env.js";
import { Issue } from "../../domain/entities/Issue.js";
import { ScrumSprintInsight } from "../../domain/metrics/SourceMetrics.js";

interface AgileBoardResponse {
  values?: Array<{
    id: number;
    name: string;
    type: string;
    location?: {
      projectKey?: string;
    };
  }>;
}

interface AgileSprintsResponse {
  values?: Array<{
    id: number;
    name: string;
    state: "active" | "future" | "closed";
  }>;
}

interface AgileSprintIssuesResponse {
  issues?: Array<{
    key: string;
    fields?: {
      resolutiondate?: string | null;
      status?: {
        name?: string;
      };
    };
  }>;
}

type AgileSprint = NonNullable<AgileSprintsResponse["values"]>[number];
type AgileSprintIssue = NonNullable<AgileSprintIssuesResponse["issues"]>[number];

export async function fetchScrumSprintInsight(
  config: AppConfig,
  source: JiraSourceConfig,
  sourceIssues: Issue[]
): Promise<ScrumSprintInsight | null> {
  const board = await findBoardForProject(config, source.projectKey);

  if (!board) {
    return null;
  }

  const sprints = await fetchBoardSprints(config, board.id);
  const activeSprint = sprints.find((sprint) => sprint.state === "active") ?? null;
  const futureSprintCount = sprints.filter((sprint) => sprint.state === "future").length;

  if (!activeSprint) {
    return {
      boardId: board.id,
      boardName: board.name,
      activeSprintId: null,
      activeSprintName: null,
      futureSprintCount,
      committedIssues: null,
      completedCommittedIssues: null,
      predictabilityFromSprint: null
    };
  }

  const sprintIssues = await fetchSprintIssues(config, board.id, activeSprint.id);
  const committedIssueKeys = new Set(sprintIssues.map((issue) => issue.key));
  const completedCommittedIssues = sprintIssues.filter((issue) =>
    Boolean(issue.fields?.resolutiondate) || issue.fields?.status?.name === "Done"
  ).length;
  const committedIssues = sprintIssues.length;

  void sourceIssues;

  return {
    boardId: board.id,
    boardName: board.name,
    activeSprintId: activeSprint.id,
    activeSprintName: activeSprint.name,
    futureSprintCount,
    committedIssues,
    completedCommittedIssues,
    predictabilityFromSprint:
      committedIssues === 0 ? 0 : completedCommittedIssues / committedIssues
  };
}

async function findBoardForProject(
  config: AppConfig,
  projectKey: string
): Promise<{ id: number; name: string } | null> {
  const url = new URL("/rest/agile/1.0/board", config.jiraBaseUrl);
  url.searchParams.set("maxResults", "100");
  url.searchParams.set("includePrivate", "true");

  const response = await fetch(url, {
    headers: {
      "Accept": "application/json",
      "Authorization": `Basic ${getBasicAuthToken(config)}`
    }
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Failed to fetch Jira boards: ${response.status} ${body.slice(0, 1000)}`);
  }

  const payload = (await response.json()) as AgileBoardResponse;
  const board = (payload.values ?? []).find(
    (item) => item.location?.projectKey === projectKey
  );

  return board ? { id: board.id, name: board.name } : null;
}

async function fetchBoardSprints(
  config: AppConfig,
  boardId: number
): Promise<AgileSprint[]> {
  const url = new URL(`/rest/agile/1.0/board/${boardId}/sprint`, config.jiraBaseUrl);
  url.searchParams.set("maxResults", "50");

  const response = await fetch(url, {
    headers: {
      "Accept": "application/json",
      "Authorization": `Basic ${getBasicAuthToken(config)}`
    }
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(
      `Failed to fetch Jira sprints for board ${boardId}: ${response.status} ${body.slice(0, 1000)}`
    );
  }

  const payload = (await response.json()) as AgileSprintsResponse;
  return payload.values ?? [];
}

async function fetchSprintIssues(
  config: AppConfig,
  boardId: number,
  sprintId: number
): Promise<AgileSprintIssue[]> {
  const url = new URL(
    `/rest/agile/1.0/board/${boardId}/sprint/${sprintId}/issue`,
    config.jiraBaseUrl
  );
  url.searchParams.set("maxResults", "100");

  const response = await fetch(url, {
    headers: {
      "Accept": "application/json",
      "Authorization": `Basic ${getBasicAuthToken(config)}`
    }
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(
      `Failed to fetch Jira sprint issues for board ${boardId} sprint ${sprintId}: ${response.status} ${body.slice(0, 1000)}`
    );
  }

  const payload = (await response.json()) as AgileSprintIssuesResponse;
  return payload.issues ?? [];
}

function getBasicAuthToken(config: AppConfig): string {
  return Buffer.from(`${config.jiraEmail}:${config.jiraApiToken}`).toString("base64");
}

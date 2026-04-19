import { JiraSourceConfig, loadConfig } from "../config/env.js";
import { loadDotEnv } from "../config/loadDotEnv.js";
import { createJiraIssue, transitionJiraIssue } from "../services/jira/jiraApi.js";

type SimulationMode = "kanban" | "scrum" | "all";

interface SimulationPlan {
  source: JiraSourceConfig;
  steps: Array<() => Promise<void>>;
}

async function main(): Promise<void> {
  loadDotEnv();
  const config = loadConfig();
  const mode = normalizeMode(process.argv[2]);

  assertRequired(config.jiraBaseUrl, "JIRA_BASE_URL");
  assertRequired(config.jiraEmail, "JIRA_EMAIL");
  assertRequired(config.jiraApiToken, "JIRA_API_TOKEN");

  const candidateSources = config.jiraSources.filter((source) =>
    mode === "all" ? true : source.methodology === mode
  );

  if (candidateSources.length === 0) {
    throw new Error(`No Jira sources available for simulation mode "${mode}".`);
  }

  for (const source of candidateSources) {
    const plan = buildSimulationPlan(config.jiraStoryPointsField, source);
    console.log("");
    console.log(
      `Simulating source ${source.key} (${source.methodology}, project=${source.projectKey})`
    );

    for (const step of plan.steps) {
      await step();
    }
  }
}

function buildSimulationPlan(
  storyPointsField: string,
  source: JiraSourceConfig
): SimulationPlan {
  void storyPointsField;

  if (source.methodology === "scrum") {
    return buildScrumPlan(source);
  }

  return buildKanbanPlan(source);
}

function buildKanbanPlan(source: JiraSourceConfig): SimulationPlan {
  const prefix = `AI Delivery Analyst ${source.key} kanban`;
  const createdKeys: string[] = [];

  return {
    source,
    steps: [
      async () => {
        const key = await createAndLog(source, `${prefix} flow task 1`, 3);
        createdKeys.push(key);
      },
      async () => {
        const key = await createAndLog(source, `${prefix} flow task 2`, 5);
        createdKeys.push(key);
      },
      async () => {
        const key = await createAndLog(source, `${prefix} blocked task`, 8);
        createdKeys.push(key);
      },
      async () => {
        await transitionAndLog(source, createdKeys[0], "In Progress");
        await transitionAndLog(source, createdKeys[0], "Done");
      },
      async () => {
        await transitionAndLog(source, createdKeys[1], "In Progress");
      },
      async () => {
        console.log(
          `Kanban scenario finished for ${source.key}: one task done, one in progress, one remaining in backlog.`
        );
      }
    ]
  };
}

function buildScrumPlan(source: JiraSourceConfig): SimulationPlan {
  const prefix = `AI Delivery Analyst ${source.key} scrum`;
  const createdKeys: string[] = [];

  return {
    source,
    steps: [
      async () => {
        const key = await createAndLog(source, `${prefix} sprint task 1`, 3);
        createdKeys.push(key);
      },
      async () => {
        const key = await createAndLog(source, `${prefix} sprint task 2`, 5);
        createdKeys.push(key);
      },
      async () => {
        const key = await createAndLog(source, `${prefix} spillover task`, 8);
        createdKeys.push(key);
      },
      async () => {
        await transitionAndLog(source, createdKeys[0], "In Progress");
        await transitionAndLog(source, createdKeys[0], "Done");
      },
      async () => {
        await transitionAndLog(source, createdKeys[1], "In Progress");
        await transitionAndLog(source, createdKeys[1], "Done");
      },
      async () => {
        await transitionAndLog(source, createdKeys[2], "In Progress");
      },
      async () => {
        console.log(
          `Scrum scenario finished for ${source.key}: two tasks completed, one left in progress to emulate incomplete sprint scope.`
        );
      }
    ]
  };
}

async function createAndLog(
  source: JiraSourceConfig,
  summary: string,
  storyPoints: number
): Promise<string> {
  const config = loadConfig();
  const key = await createJiraIssue(config, source, summary, storyPoints);
  console.log(`Created ${key}: ${summary} (${storyPoints} SP)`);
  return key;
}

async function transitionAndLog(
  source: JiraSourceConfig,
  issueKey: string | undefined,
  transitionName: string
): Promise<void> {
  const config = loadConfig();

  if (!issueKey) {
    throw new Error(`Cannot transition issue for ${source.key}: missing issue key.`);
  }

  await transitionJiraIssue(config, issueKey, transitionName);
  console.log(`Transitioned ${issueKey} -> ${transitionName}`);
}

function normalizeMode(rawValue: string | undefined): SimulationMode {
  if (rawValue === "scrum" || rawValue === "kanban" || rawValue === "all") {
    return rawValue;
  }

  return "all";
}

function assertRequired(value: string, name: string): void {
  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`);
  }
}

main().catch((error) => {
  console.error("Jira simulation failed.", error);
  process.exitCode = 1;
});

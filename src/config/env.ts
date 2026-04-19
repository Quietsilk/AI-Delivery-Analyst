export type DeliveryMethodology = "scrum" | "kanban";

export interface JiraSourceConfig {
  key: string;
  projectKey: string;
  methodology: DeliveryMethodology;
  jql: string;
  startedStatuses: string[];
}

export interface AppConfig {
  jiraBaseUrl: string;
  jiraEmail: string;
  jiraApiToken: string;
  jiraProjectKey: string;
  jiraJql: string;
  jiraStartedStatuses: string[];
  jiraSources: JiraSourceConfig[];
  jiraStoryPointsField: string;
  jiraOriginalEstimateField: string;
  jiraPageSize: number;
  openAiApiKey: string;
  openAiBaseUrl: string;
  openAiModel: string;
  openAiReasoningEffort: "none" | "low" | "medium" | "high" | "xhigh";
  reportChannel: "telegram" | "slack";
}

function getEnv(name: string, fallback = ""): string {
  return process.env[name] ?? fallback;
}

function getListEnv(name: string, fallback: string[]): string[] {
  const value = process.env[name];

  if (!value) {
    return fallback;
  }

  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function getNumberEnv(name: string, fallback: number): number {
  const value = process.env[name];
  const parsed = Number(value);

  if (!value || Number.isNaN(parsed) || parsed <= 0) {
    return fallback;
  }

  return parsed;
}

function getReasoningEffortEnv(
  name: string,
  fallback: AppConfig["openAiReasoningEffort"]
): AppConfig["openAiReasoningEffort"] {
  const value = process.env[name];

  if (
    value === "none" ||
    value === "low" ||
    value === "medium" ||
    value === "high" ||
    value === "xhigh"
  ) {
    return value;
  }

  return fallback;
}

function parseJiraSources(
  value: string,
  fallbackProjectKey: string,
  fallbackJql: string,
  fallbackStartedStatuses: string[]
): JiraSourceConfig[] {
  if (!value.trim()) {
    return [
      {
        key: fallbackProjectKey || "default",
        projectKey: fallbackProjectKey,
        methodology: "kanban",
        jql: fallbackJql,
        startedStatuses: fallbackStartedStatuses
      }
    ];
  }

  return value
    .split(";")
    .map((source) => source.trim())
    .filter(Boolean)
    .map((source) => {
      const [keyPart, methodologyPart, projectKeyPart, jqlPart, statusesPart] =
        source.split("|").map((part) => part.trim());

      const projectKey = projectKeyPart || keyPart;
      const methodology = normalizeMethodology(methodologyPart);
      const startedStatuses =
        statusesPart && statusesPart.length > 0
          ? statusesPart.split(",").map((status) => status.trim()).filter(Boolean)
          : fallbackStartedStatuses;

      return {
        key: keyPart || projectKey || "default",
        projectKey,
        methodology,
        jql:
          jqlPart && jqlPart.length > 0
            ? jqlPart
            : projectKey
              ? `project = "${projectKey}" ORDER BY updated DESC`
              : fallbackJql,
        startedStatuses
      };
    });
}

function normalizeMethodology(value: string | undefined): DeliveryMethodology {
  return value === "scrum" ? "scrum" : "kanban";
}

export function loadConfig(): AppConfig {
  const jiraProjectKey = getEnv("JIRA_PROJECT_KEY");
  const jiraJql = getEnv(
    "JIRA_JQL",
    jiraProjectKey
      ? `project = "${jiraProjectKey}" ORDER BY updated DESC`
      : "ORDER BY updated DESC"
  );
  const jiraStartedStatuses = getListEnv("JIRA_STARTED_STATUSES", ["In Progress"]);

  return {
    jiraBaseUrl: getEnv("JIRA_BASE_URL"),
    jiraEmail: getEnv("JIRA_EMAIL"),
    jiraApiToken: getEnv("JIRA_API_TOKEN"),
    jiraProjectKey,
    jiraJql,
    jiraStartedStatuses,
    jiraSources: parseJiraSources(
      getEnv("JIRA_SOURCES"),
      jiraProjectKey,
      jiraJql,
      jiraStartedStatuses
    ),
    jiraStoryPointsField: getEnv("JIRA_STORY_POINTS_FIELD", "customfield_10016"),
    jiraOriginalEstimateField: getEnv(
      "JIRA_ORIGINAL_ESTIMATE_FIELD",
      "timeoriginalestimate"
    ),
    jiraPageSize: getNumberEnv("JIRA_PAGE_SIZE", 50),
    openAiApiKey: getEnv("OPENAI_API_KEY"),
    openAiBaseUrl: getEnv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    openAiModel: getEnv("OPENAI_MODEL", "gpt-5-mini"),
    openAiReasoningEffort: getReasoningEffortEnv(
      "OPENAI_REASONING_EFFORT",
      "medium"
    ),
    reportChannel: (getEnv("REPORT_CHANNEL", "telegram") as "telegram" | "slack")
  };
}

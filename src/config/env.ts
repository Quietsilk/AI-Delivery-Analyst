export interface AppConfig {
  jiraBaseUrl: string;
  jiraEmail: string;
  jiraApiToken: string;
  jiraProjectKey: string;
  jiraJql: string;
  jiraStartedStatuses: string[];
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

export function loadConfig(): AppConfig {
  const jiraProjectKey = getEnv("JIRA_PROJECT_KEY");

  return {
    jiraBaseUrl: getEnv("JIRA_BASE_URL"),
    jiraEmail: getEnv("JIRA_EMAIL"),
    jiraApiToken: getEnv("JIRA_API_TOKEN"),
    jiraProjectKey,
    jiraJql: getEnv(
      "JIRA_JQL",
      jiraProjectKey
        ? `project = "${jiraProjectKey}" ORDER BY updated DESC`
        : "ORDER BY updated DESC"
    ),
    jiraStartedStatuses: getListEnv("JIRA_STARTED_STATUSES", ["In Progress"]),
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

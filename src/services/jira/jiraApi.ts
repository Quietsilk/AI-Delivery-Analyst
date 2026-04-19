import { AppConfig, JiraSourceConfig } from "../../config/env.js";

interface JiraTransition {
  id: string;
  name: string;
}

interface JiraTransitionsResponse {
  transitions?: JiraTransition[];
}

interface JiraCreateIssueResponse {
  key: string;
}

export async function createJiraIssue(
  config: AppConfig,
  source: JiraSourceConfig,
  summary: string,
  storyPoints?: number
): Promise<string> {
  const primaryAttempt = await createIssueRequest(config, source, summary, storyPoints);

  if (primaryAttempt.ok) {
    const payload = JSON.parse(primaryAttempt.body) as JiraCreateIssueResponse;
    return payload.key;
  }

  if (
    typeof storyPoints === "number" &&
    primaryAttempt.body.includes(config.jiraStoryPointsField)
  ) {
    const fallbackAttempt = await createIssueRequest(config, source, summary);

    if (fallbackAttempt.ok) {
      const payload = JSON.parse(fallbackAttempt.body) as JiraCreateIssueResponse;
      return payload.key;
    }

    throw new Error(
      `Failed to create Jira issue for ${source.key}: ${fallbackAttempt.response.status} ${fallbackAttempt.body.slice(0, 1000)}`
    );
  }

  throw new Error(
    `Failed to create Jira issue for ${source.key}: ${primaryAttempt.response.status} ${primaryAttempt.body.slice(0, 1000)}`
  );
}

export async function transitionJiraIssue(
  config: AppConfig,
  issueKey: string,
  transitionName: string
): Promise<void> {
  const transitions = await getJiraTransitions(config, issueKey);
  const transition = transitions.find((item) => item.name === transitionName);

  if (!transition) {
    throw new Error(
      `Transition "${transitionName}" is not available for ${issueKey}. Available: ${transitions
        .map((item) => item.name)
        .join(", ")}`
    );
  }

  const response = await fetch(
    new URL(`/rest/api/3/issue/${issueKey}/transitions`, config.jiraBaseUrl),
    {
      method: "POST",
      headers: {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": `Basic ${getBasicAuthToken(config)}`
      },
      body: JSON.stringify({
        transition: { id: transition.id }
      })
    }
  );

  if (!response.ok) {
    const body = await response.text();
    throw new Error(
      `Failed to transition ${issueKey} to ${transitionName}: ${response.status} ${body.slice(0, 1000)}`
    );
  }
}

async function getJiraTransitions(
  config: AppConfig,
  issueKey: string
): Promise<JiraTransition[]> {
  const response = await fetch(
    new URL(`/rest/api/3/issue/${issueKey}/transitions`, config.jiraBaseUrl),
    {
      method: "GET",
      headers: {
        "Accept": "application/json",
        "Authorization": `Basic ${getBasicAuthToken(config)}`
      }
    }
  );

  if (!response.ok) {
    const body = await response.text();
    throw new Error(
      `Failed to fetch transitions for ${issueKey}: ${response.status} ${body.slice(0, 1000)}`
    );
  }

  const payload = (await response.json()) as JiraTransitionsResponse;
  return payload.transitions ?? [];
}

function getBasicAuthToken(config: AppConfig): string {
  return Buffer.from(`${config.jiraEmail}:${config.jiraApiToken}`).toString("base64");
}

async function createIssueRequest(
  config: AppConfig,
  source: JiraSourceConfig,
  summary: string,
  storyPoints?: number
): Promise<{ ok: boolean; response: Response; body: string }> {
  const response = await fetch(new URL("/rest/api/3/issue", config.jiraBaseUrl), {
    method: "POST",
    headers: {
      "Accept": "application/json",
      "Content-Type": "application/json",
      "Authorization": `Basic ${getBasicAuthToken(config)}`
    },
    body: JSON.stringify({
      fields: {
        project: { key: source.projectKey },
        issuetype: { name: "Task" },
        summary,
        ...(typeof storyPoints === "number"
          ? { [config.jiraStoryPointsField]: storyPoints }
          : {})
      }
    })
  });

  const body = await response.text();

  return {
    ok: response.ok,
    response,
    body
  };
}

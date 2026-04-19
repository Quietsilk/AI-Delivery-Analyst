import { AppConfig, JiraSourceConfig } from "../../config/env.js";
import { Issue } from "../../domain/entities/Issue.js";
import { JiraClient } from "./JiraClient.js";

export async function fetchSourceIssues(
  config: AppConfig,
  source: JiraSourceConfig
): Promise<Issue[]> {
  const client = new JiraClient(config, source);
  return client.fetchIssues();
}

import { AppConfig } from "../config/env.js";
import { calculateMetrics } from "../domain/metrics/calculateMetrics.js";
import { DeliveryAnalyst } from "../services/analysis/DeliveryAnalyst.js";
import { JiraClient } from "../services/jira/JiraClient.js";
import { formatReport } from "../services/reporting/ReportFormatter.js";
import { ReportPublisher } from "../services/reporting/ReportPublisher.js";

export async function runDailyDeliveryAnalysis(config: AppConfig): Promise<void> {
  const jiraClient = new JiraClient(config);
  const analyst = new DeliveryAnalyst(config);
  const publisher = new ReportPublisher(config);

  const issues = await jiraClient.fetchIssues();
  const metrics = calculateMetrics(issues);
  const analysis = await analyst.analyze(metrics, issues);
  const report = formatReport(metrics, analysis, issues);

  await publisher.publish(report);
}

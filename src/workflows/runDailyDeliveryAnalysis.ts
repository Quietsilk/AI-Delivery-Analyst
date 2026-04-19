import { AppConfig } from "../config/env.js";
import { SourceMetrics } from "../domain/metrics/SourceMetrics.js";
import { calculateMetrics } from "../domain/metrics/calculateMetrics.js";
import { DeliveryAnalyst } from "../services/analysis/DeliveryAnalyst.js";
import { fetchScrumSprintInsight } from "../services/jira/agileInsights.js";
import { fetchSourceIssues } from "../services/jira/fetchSourceIssues.js";
import { formatReport } from "../services/reporting/ReportFormatter.js";
import { ReportPublisher } from "../services/reporting/ReportPublisher.js";

export async function runDailyDeliveryAnalysis(config: AppConfig): Promise<void> {
  const analyst = new DeliveryAnalyst(config);
  const publisher = new ReportPublisher(config);

  const sources: SourceMetrics[] = [];

  for (const source of config.jiraSources) {
    const issues = await fetchSourceIssues(config, source);
    const scrumInsight =
      source.methodology === "scrum"
        ? await fetchScrumSprintInsight(config, source, issues)
        : null;
    const baseMetrics = calculateMetrics(issues);

    sources.push({
      sourceKey: source.key,
      projectKey: source.projectKey,
      methodology: source.methodology,
      metrics: {
        ...baseMetrics,
        predictability:
          scrumInsight?.predictabilityFromSprint ?? baseMetrics.predictability
      },
      issues,
      scrumInsight
    });
  }

  const issues = sources.flatMap((source) => source.issues);
  const metrics = calculateMetrics(issues);
  const analysis = await analyst.analyze(metrics, issues, sources);
  const report = formatReport(metrics, analysis, issues, sources);

  await publisher.publish(report);
}

import { AppConfig } from "../../config/env.js";

export class ReportPublisher {
  constructor(private readonly config: AppConfig) {}

  async publish(report: string): Promise<void> {
    // TODO: Route to Telegram or Slack based on config.reportChannel.
    console.log(`Publishing report to ${this.config.reportChannel}:\n${report}`);
  }
}

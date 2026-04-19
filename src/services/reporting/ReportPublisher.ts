import { AppConfig } from "../../config/env.js";

const TELEGRAM_MAX_LENGTH = 4096;

export class ReportPublisher {
  constructor(private readonly config: AppConfig) {}

  async publish(report: string): Promise<void> {
    if (this.config.reportChannel === "telegram") {
      await this.publishToTelegram(report);
    } else if (this.config.reportChannel === "slack") {
      await this.publishToSlack(report);
    } else {
      console.log(report);
    }
  }

  private async publishToTelegram(report: string): Promise<void> {
    const { telegramBotToken, telegramChatId } = this.config;

    if (!telegramBotToken || !telegramChatId) {
      throw new Error(
        "Telegram delivery requires TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to be set."
      );
    }

    const url = `https://api.telegram.org/bot${telegramBotToken}/sendMessage`;
    const chunks = splitIntoChunks(report, TELEGRAM_MAX_LENGTH);

    for (const chunk of chunks) {
      const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          chat_id: telegramChatId,
          text: chunk
        })
      });

      if (!response.ok) {
        const body = await response.text();
        throw new Error(
          `Telegram delivery failed with status ${response.status}: ${body.slice(0, 300)}`
        );
      }
    }

    console.log(`Report sent to Telegram (chat_id=${telegramChatId}, chunks=${chunks.length})`);
  }

  private async publishToSlack(report: string): Promise<void> {
    const { slackWebhookUrl } = this.config;

    if (!slackWebhookUrl) {
      throw new Error("Slack delivery requires SLACK_WEBHOOK_URL to be set.");
    }

    const response = await fetch(slackWebhookUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: report })
    });

    if (!response.ok) {
      const body = await response.text();
      throw new Error(
        `Slack delivery failed with status ${response.status}: ${body.slice(0, 300)}`
      );
    }

    console.log("Report sent to Slack.");
  }
}

function splitIntoChunks(text: string, maxLength: number): string[] {
  if (text.length <= maxLength) return [text];

  const chunks: string[] = [];
  let remaining = text;

  while (remaining.length > 0) {
    if (remaining.length <= maxLength) {
      chunks.push(remaining);
      break;
    }

    const slice = remaining.slice(0, maxLength);
    const lastNewline = slice.lastIndexOf("\n");
    const cutAt = lastNewline > 0 ? lastNewline : maxLength;

    chunks.push(remaining.slice(0, cutAt));
    remaining = remaining.slice(cutAt).trimStart();
  }

  return chunks;
}

import { AppConfig } from "../../config/env.js";
import { Issue } from "../../domain/entities/Issue.js";
import { DeliveryMetrics } from "../../domain/metrics/types.js";
import { buildPrompt } from "./buildPrompt.js";

interface OpenAiResponsesApiResult {
  output_text?: string;
}

export class DeliveryAnalyst {
  constructor(private readonly config: AppConfig) {}

  async analyze(metrics: DeliveryMetrics, issues: Issue[]): Promise<string> {
    const prompt = buildPrompt(metrics, issues);

    if (!this.config.openAiApiKey) {
      return [
        "AI analysis skipped because `OPENAI_API_KEY` is not configured.",
        "",
        prompt
      ].join("\n");
    }

    const response = await fetch(`${this.config.openAiBaseUrl}/responses`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${this.config.openAiApiKey}`
      },
      body: JSON.stringify({
        model: this.config.openAiModel,
        reasoning: {
          effort: this.config.openAiReasoningEffort
        },
        instructions:
          "You are an expert delivery analyst. Produce concise, specific, non-generic delivery guidance for engineering teams.",
        input: prompt
      })
    });

    if (!response.ok) {
      const body = await response.text();
      throw new Error(
        `OpenAI analysis failed with status ${response.status}: ${body.slice(0, 500)}`
      );
    }

    const result = (await response.json()) as OpenAiResponsesApiResult;

    if (!result.output_text) {
      throw new Error("OpenAI analysis failed: response did not include output_text.");
    }

    return result.output_text.trim();
  }
}

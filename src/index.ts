import { loadDotEnv } from "./config/loadDotEnv.js";
import { loadConfig } from "./config/env.js";
import { runDailyDeliveryAnalysis } from "./workflows/runDailyDeliveryAnalysis.js";

async function main(): Promise<void> {
  loadDotEnv();
  const config = loadConfig();
  await runDailyDeliveryAnalysis(config);
}

main().catch((error) => {
  console.error("AI Delivery Analyst failed to start.", error);
  process.exitCode = 1;
});

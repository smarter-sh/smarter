/** Example log lines, as the log stream api sends them. See smarter.apps.dashboard.views.terminal_emulator. */
export const STREAM_URL = "/dashboard/logs/api/stream/";

export const bulkLogs = [
  { message: "[stream] connected", level: "INFO" },
  { message: "INFO smarter.apps.llmclient: LLMClient example deployed", level: "INFO" },
  { message: "WARNING smarter.apps.provider: openai rate limited, retrying", level: "WARNING" },
];

export const liveLog = { message: "INFO smarter.apps.prompt: prompt completed in 1.2s", level: "INFO" };

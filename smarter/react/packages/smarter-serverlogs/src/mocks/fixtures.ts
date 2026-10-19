/**
 * Example data for this package's stories, tests and development page: the server log stream's url, and the
 * records that it sends. See smarter.apps.dashboard.views.terminal_emulator.api.streams.
 */
import type { LogEvent } from "../lib/logStream";

/** The server log stream. */
export const LOG_STREAM_URL = "http://localhost:9357/dashboard/logs/api/stream/";

/** The user's recent server logs, which the log stream sends first, as its "bulk" event. */
export const bulkLogs: LogEvent[] = [
  {
    message: "2026-01-01 12:00:00,000 INFO \u001b[1;34msmarter.apps.prompt\u001b[0m prompt started",
    level: "INFO",
    logger: "smarter.apps.prompt",
    timestamp: 1767268800,
  },
  {
    message: "2026-01-01 12:00:01,000 WARNING plugin stackademy_sql is slow",
    level: "WARNING",
    logger: "smarter.apps.plugin",
    timestamp: 1767268801,
  },
];

/** A server log record that arrives after the bulk history. */
export const liveLog: LogEvent = {
  message: "2026-01-01 12:00:02,000 ERROR \u001b[31mprompt finished\u001b[0m",
  level: "ERROR",
  logger: "smarter.apps.prompt",
  timestamp: 1767268802,
};

/** A record with a long line, and a block of pretty-printed JSON, which the viewer collapses. */
export const jsonLog: LogEvent = {
  message: `2026-01-01 12:00:03,000 DEBUG smarter.apps.prompt request body: ${JSON.stringify(
    {
      model: "gpt-4o-mini",
      messages: [{ role: "user", content: "What's the weather in San Francisco? ".repeat(6) }],
    },
    null,
    2,
  )}`,
  level: "DEBUG",
  logger: "smarter.apps.prompt",
  timestamp: 1767268803,
};

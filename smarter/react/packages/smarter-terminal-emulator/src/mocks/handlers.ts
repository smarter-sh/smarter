/**
 * MSW request handlers for the log stream, a server-sent events stream, for Storybook. Tests use
 * mocks/fakes.ts instead, because jsdom has no EventSource.
 */
import { sse } from "msw";

import { STREAM_URL, bulkLogs, liveLog } from "./fixtures";

export const streamHandlers = [
  sse<{ message: string; bulk: string }>(STREAM_URL, ({ client }) => {
    client.send({ event: "bulk", data: JSON.stringify(bulkLogs) });
    setTimeout(() => client.send({ data: JSON.stringify(liveLog) }), 1000);
  }),
];

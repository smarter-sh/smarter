/**
 * The server logs of one prompt, as Server-Sent Events, for the Prompt Passthrough's "Server Logs" tab.
 *
 * The stream is the one that the workbench's Console reads: its first event is a "bulk" event with
 * the recent history, and each later event is one log record, as JSON. See
 * smarter.apps.dashboard.views.terminal_emulator.api.streams.stream_user_logs. Its "request_id"
 * query parameter narrows it to the records of one request: the request whose X-Smarter-RequestId
 * header had that id.
 *
 * Adapted from smarter-chat's src/lib/logStream.ts, which is published separately, as
 * @smarter.sh/ui-chat. Keep the two consistent.
 */
import { useEffect, useState } from "react";

import { gettext } from "@smarter/common";

/** A log record. Records that aren't JSON are displayed as their message. */
export interface LogEvent {
  message: string;
  level?: string;
  levelname?: string;
  timestamp?: number | string;
  logger?: string;
  [key: string]: unknown;
}

/** The most records to keep. Older records are dropped. */
export const MAX_LOG_EVENTS = 2000;

/** The log level of the stream: every record of the prompt. */
export const PROMPT_LOG_LEVEL = "DEBUG";

/**
 * The log stream's url, for the records of one request, at or above the given log level. Without
 * a stream url, or a request id, there is no stream.
 */
export function logStreamUrlForRequest(
  streamUrl: string | null,
  requestId: string | null,
  level: string = PROMPT_LOG_LEVEL,
): string | null {
  if (!streamUrl || !requestId) return null;
  const url = new URL(streamUrl, window.location.href);
  url.searchParams.set("request_id", requestId);
  url.searchParams.set("level", level);
  return url.toString();
}

/** A new request id: 32 hexadecimal digits, as Django's SmarterRequestMixin.generate_smarter_request_id() makes. */
export function newRequestId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID().replace(/-/g, "");
  }
  return Array.from({ length: 32 }, () => Math.floor(Math.random() * 16).toString(16)).join("");
}

function parseLogEvent(data: string): LogEvent {
  try {
    const parsed = JSON.parse(data) as unknown;
    if (parsed && typeof parsed === "object" && "message" in parsed) return parsed as LogEvent;
  } catch {
    // plain text
  }
  return { message: data };
}

function keepRecent(logs: LogEvent[]): LogEvent[] {
  return logs.length > MAX_LOG_EVENTS ? logs.slice(logs.length - MAX_LOG_EVENTS) : logs;
}

/**
 * The log stream's records, and its connection state. Connects only while streamUrl is set.
 *
 * A new url, e.g. for the next prompt, starts with no records.
 */
export function useLogStream(streamUrl: string | null) {
  const [logs, setLogs] = useState<LogEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [previousUrl, setPreviousUrl] = useState(streamUrl);

  // a new stream: its records replace the previous stream's. Adjusted while rendering, rather than in an effect.
  if (streamUrl !== previousUrl) {
    setPreviousUrl(streamUrl);
    setLogs([]);
    setConnected(false);
    setError(null);
  }

  useEffect(() => {
    if (!streamUrl || typeof EventSource === "undefined") return;
    const source = new EventSource(streamUrl, { withCredentials: true });

    source.onopen = () => {
      setConnected(true);
      setError(null);
    };
    source.addEventListener("bulk", (event: MessageEvent<string>) => {
      try {
        const records = JSON.parse(event.data) as unknown;
        if (!Array.isArray(records)) return;
        setLogs(keepRecent(records.map((record) => parseLogEvent(JSON.stringify(record)))));
      } catch {
        // a malformed history. Live records still arrive.
      }
    });
    source.onmessage = (event: MessageEvent<string>) => {
      const log = parseLogEvent(event.data);
      setLogs((previous) => keepRecent([...previous, log]));
    };
    source.onerror = () => {
      // the browser reconnects by itself, after the server's retry interval.
      setConnected(false);
      setError(gettext("The log stream disconnected. Reconnecting..."));
    };

    return () => {
      source.close();
      setConnected(false);
    };
  }, [streamUrl]);

  return { logs, connected, error };
}

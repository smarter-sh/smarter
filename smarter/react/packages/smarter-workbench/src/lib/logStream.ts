/**
 * The user's server logs, as Server-Sent Events, for the Console's "Server Logs" tab.
 *
 * The stream is the one that the Smarter web console's log viewer reads: its first event is a
 * "bulk" event with the recent history, and each later event is one log record, as JSON. See
 * smarter.apps.dashboard.views.terminal_emulator.api.streams.stream_user_logs.
 *
 * The stream sends the records at or above its "level" query parameter, or, without it, at or above
 * the server's log level, smarter_settings.log_level. Sandbox mode asks for DEBUG. Its "session_key"
 * query parameter narrows it to the records of one chat: the requests to the LLMClient's api with
 * that chat session key. Without it, the stream sends every record of the user, e.g. other chats'.
 */
import { useCallback, useEffect, useRef, useState } from "react";

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

/** The log level of the stream in sandbox mode. Production mode uses the server's log level. */
export const SANDBOX_LOG_LEVEL = "DEBUG";

/**
 * The log stream's url, for the records at or above the given log level, e.g. "DEBUG". Without a
 * level, the url is unchanged, and the stream sends the records at or above the server's log level.
 */
export function logStreamUrlForLevel(streamUrl: string | null, level: string | null = null): string | null {
  if (!streamUrl || !level) return streamUrl;
  const url = new URL(streamUrl, window.location.href);
  url.searchParams.set("level", level);
  return url.toString();
}

/**
 * The log stream's url, for the records of one chat session, at or above the given log level. Without
 * a stream url, or a session key, e.g. before the chat's configuration loads, there is no stream.
 */
export function logStreamUrlForChat(
  streamUrl: string | null,
  sessionKey: string | null,
  level: string | null = null,
): string | null {
  if (!streamUrl || !sessionKey) return null;
  const url = new URL(logStreamUrlForLevel(streamUrl, level) ?? streamUrl, window.location.href);
  url.searchParams.set("session_key", sessionKey);
  return url.toString();
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

/** Whether a record was logged before the given time, in seconds, as Python's record.created is. */
function loggedBefore(log: LogEvent, time: number): boolean {
  const timestamp = typeof log.timestamp === "string" ? Number(log.timestamp) : log.timestamp;
  return typeof timestamp === "number" && Number.isFinite(timestamp) && timestamp < time;
}

function keepRecent(logs: LogEvent[]): LogEvent[] {
  return logs.length > MAX_LOG_EVENTS ? logs.slice(logs.length - MAX_LOG_EVENTS) : logs;
}

/**
 * The log stream's records, and its connection state. Connects only while streamUrl is set.
 *
 * A new url, e.g. for a new chat session, starts with no records. clear() removes the records. The
 * records that were logged before then are not displayed again, even when a reconnection replays the
 * history.
 */
export function useLogStream(streamUrl: string | null) {
  const [logs, setLogs] = useState<LogEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const clearedAt = useRef(0);
  const [previousUrl, setPreviousUrl] = useState(streamUrl);

  // a new stream: its records replace the previous stream's. Adjusted while rendering, rather than in an effect.
  if (streamUrl !== previousUrl) {
    setPreviousUrl(streamUrl);
    setLogs([]);
    setConnected(false);
    setError(null);
  }

  const clear = useCallback(() => {
    clearedAt.current = Date.now() / 1000;
    setLogs([]);
  }, []);

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
        const history = records.map((record) => parseLogEvent(JSON.stringify(record)));
        setLogs(keepRecent(history.filter((log) => !loggedBefore(log, clearedAt.current))));
      } catch {
        // a malformed history. Live records still arrive.
      }
    });
    source.onmessage = (event: MessageEvent<string>) => {
      const log = parseLogEvent(event.data);
      if (loggedBefore(log, clearedAt.current)) return;
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

  return { logs, connected, error, clear };
}

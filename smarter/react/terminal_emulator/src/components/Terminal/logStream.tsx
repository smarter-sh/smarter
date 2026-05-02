//-----------------------------------------------------------------------------
// Log Stream Hook.
//
// This hook connects to a log stream API using Server-Sent Events (SSE) and
// manages the state of incoming log messages, connection status, and errors.
// It provides a simple interface for components to consume real-time log data.
//-----------------------------------------------------------------------------
import { useEffect, useRef, useState } from "react";

type LogEvent = {
  message: string;
  level?: string;
  timestamp?: number;
  logger?: string;
  pod?: string;
};

export function useLogStream(streamUrl: string) {
  const [logs, setLogs] = useState<LogEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    const es = new EventSource(streamUrl);
    esRef.current = es;

    es.onopen = () => {
      setConnected(true);
      setError(null);
    };

    es.onmessage = (event) => {
      try {
        console.log("Received log event:", event.data);
        const parsed = JSON.parse(event.data) as LogEvent;
        setLogs((prev) => [...prev, parsed]);
      } catch {
        // Fallback if payload is plain text
        setLogs((prev) => [...prev, { message: event.data }]);
      }
    };

    es.onerror = () => {
      setConnected(false);
      setError("Log stream disconnected. Reconnecting...");
      // Browser will retry automatically (server says retry: 3000)
    };

    return () => {
      es.close();
      esRef.current = null;
      setConnected(false);
    };
  }, [streamUrl]);

  return { logs, connected, error };
}

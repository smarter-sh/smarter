// ----------------------------------------------------------------------------
// TerminalEmulator Component.
//
// This component renders a terminal emulator using xterm.js and connects to a
// log stream API. It displays incoming log messages in real-time and shows
// connection status. The component is styled to resemble a classic terminal
// window and is responsive to container size changes.
// ----------------------------------------------------------------------------
import { useEffect, useRef, useState } from "react";
import { FitAddon } from "@xterm/addon-fit";
import { Terminal } from "@xterm/xterm";
import "@xterm/xterm/css/xterm.css";
import { useLogStream } from "./logStream";
import "./styles.css";

// These strings are internal SSE stream status messages emitted by the server. They can
// appear in replay history from older log entries and should never surface to dashboard users.
const SUPPRESSED_STARTUP_LINES = new Set(["Waiting for log stream...", "[stream] connected"]);

interface TerminalEmulatorProps {
  apiUrl: string;
}

function TerminalEmulator({ apiUrl }: TerminalEmulatorProps) {
  const { logs, connected, error, isInitializing } = useLogStream(apiUrl);
  const [showLoading, setShowLoading] = useState(false);
  const terminalContainerRef = useRef<HTMLDivElement | null>(null);
  const terminalRef = useRef<Terminal | null>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);
  const lastLogIndexRef = useRef(0);
  const initBufferRef = useRef<string[]>([]);

  useEffect(() => {
    if (!terminalContainerRef.current) {
      return;
    }

    const term = new Terminal({
      convertEol: true,
      cursorBlink: false,
      disableStdin: true,
      fontFamily: '"JetBrains Mono", "SFMono-Regular", Menlo, monospace',
      fontSize: 13,
      lineHeight: 1.4,
      scrollback: 5000,
      theme: {
        background: "#171b20",
        foreground: "#d9e1ea",
        cursor: "#78dce8",
        black: "#1b1f24",
        red: "#ff8f8f",
        green: "#7bd88f",
        yellow: "#ffd580",
        blue: "#78dce8",
        magenta: "#c792ea",
        cyan: "#89ddff",
        white: "#d9e1ea",
        brightBlack: "#5c6773",
        brightRed: "#ff8f8f",
        brightGreen: "#7bd88f",
        brightYellow: "#ffd580",
        brightBlue: "#89ddff",
        brightMagenta: "#d8b4ff",
        brightCyan: "#89ddff",
        brightWhite: "#ffffff",
      },
    });
    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);

    term.open(terminalContainerRef.current);
    // defer fit until after browser layout
    let rafId = requestAnimationFrame(() => {
      fitAddon.fit();
    });

    terminalRef.current = term;
    fitAddonRef.current = fitAddon;

    const handleResize = () => {
      fitAddonRef.current?.fit();
    };

    const resizeObserver = new ResizeObserver(() => {
      fitAddonRef.current?.fit();
    });

    resizeObserver.observe(terminalContainerRef.current);
    window.addEventListener("resize", handleResize);

    return () => {
      cancelAnimationFrame(rafId);
      window.removeEventListener("resize", handleResize);
      resizeObserver.disconnect();
      fitAddonRef.current = null;
      terminalRef.current = null;
      term.dispose();
    };
  }, []);

  useEffect(() => {
    if (!terminalRef.current) {
      return;
    }

    const nextLogs = logs.slice(lastLogIndexRef.current);
    if (!nextLogs.length) {
      return;
    }

    const nextMessages = nextLogs
      .map((log) => log.message)
      .filter((message) => !SUPPRESSED_STARTUP_LINES.has(message.trim())); // drop internal stream noise
    lastLogIndexRef.current = logs.length;

    if (!nextMessages.length) {
      return;
    }

    if (isInitializing) {
      initBufferRef.current.push(...nextMessages);
      return;
    }

    const bufferedMessages = initBufferRef.current;
    initBufferRef.current = [];
    const allMessages = bufferedMessages.concat(nextMessages);
    const batchedOutput = `${allMessages.join("\r\n")}\r\n`;
    terminalRef.current.write(batchedOutput);
  }, [isInitializing, logs]);

  useEffect(() => {
    if (!isInitializing) {
      setShowLoading(false);
      return;
    }

    const timeoutId = window.setTimeout(() => {
      setShowLoading(true);
    }, 250);

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [isInitializing]);

  useEffect(() => {
    if (!terminalRef.current || !error) {
      return;
    }

    terminalRef.current.writeln(`\x1b[31m[stream] ${error}\x1b[0m`);
  }, [error]);

  return (
    <>
      <section className="terminal-window" aria-label="Log terminal">
        <div className="terminal-window__header">
          <div className="terminal-window__controls" aria-hidden="true">
            <span className="terminal-window__dot terminal-window__dot--close" />
            <span className="terminal-window__dot terminal-window__dot--minimize" />
            <span className="terminal-window__dot terminal-window__dot--maximize" />
          </div>
          <div className="terminal-window__title">logs@smarter:~</div>
          <div
            className={`terminal-window__status ${connected ? "is-online" : "is-offline"}`}
          >
            {connected ? "connected" : "disconnected"}
          </div>
        </div>

        <div className="terminal-window__body" role="log" aria-live="polite">
          {showLoading && (
            <div className="terminal-window__loading" aria-label="Loading logs">
              <span className="terminal-window__loading-spinner" aria-hidden="true" />
              <span>Loading logs…</span>
            </div>
          )}
          <div ref={terminalContainerRef} className="terminal-window__xterm" />
        </div>
      </section>{" "}
    </>
  );
}

export default TerminalEmulator;

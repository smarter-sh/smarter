import { useEffect, useRef } from "react";
import { FitAddon } from "@xterm/addon-fit";
import { Terminal } from "xterm";
import "xterm/css/xterm.css";
import { useLogStream } from "./logStream";
import "./styles.css";

interface TerminalEmulatorProps {
  apiUrl: string;
  csrfCookieName: string;
  csrftoken: string;
  djangoSessionCookieName: string;
  cookieDomain: string;
}

function TerminalEmulator({
  apiUrl,
  csrfCookieName,
  csrftoken,
  djangoSessionCookieName,
  cookieDomain,
}: TerminalEmulatorProps) {
  const { logs, connected, error } = useLogStream(apiUrl);
  const terminalContainerRef = useRef<HTMLDivElement | null>(null);
  const terminalRef = useRef<Terminal | null>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);
  const lastLogIndexRef = useRef(0);

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
    fitAddon.fit();
    term.writeln("\x1b[2mWaiting for log stream...\x1b[0m");

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

    nextLogs.forEach((log) => {
      terminalRef.current?.writeln(log.message);
    });

    lastLogIndexRef.current = logs.length;
  }, [logs]);

  useEffect(() => {
    if (!terminalRef.current) {
      return;
    }

    if (connected) {
      terminalRef.current.writeln("\x1b[32m[stream] connected\x1b[0m");
    }
  }, [connected]);

  useEffect(() => {
    if (!terminalRef.current || !error) {
      return;
    }

    terminalRef.current.writeln(`\x1b[31m[stream] ${error}\x1b[0m`);
  }, [error]);

  return (
    <>
      <section className="terminal-emulator">
        <div className="row">
          <div className="col-12">
            <h4>Terminal Emulator Component</h4>
            <p>apiUrl: {apiUrl}</p>
            <p>csrfCookieName: {csrfCookieName}</p>
            <p>djangoSessionCookieName: {djangoSessionCookieName}</p>
            <p>cookieDomain: {cookieDomain}</p>
            <p>csrftoken: {csrftoken}</p>
            <p>Connected: {connected ? "Yes" : "No"}</p>
          </div>
        </div>
      </section>


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
          <div ref={terminalContainerRef} className="terminal-window__xterm" />
        </div>
      </section>{" "}
    </>
  );
}

export default TerminalEmulator;

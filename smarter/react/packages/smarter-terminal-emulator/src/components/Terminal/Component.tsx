// ----------------------------------------------------------------------------
// TerminalEmulator Component.
//
// This component renders a terminal emulator using xterm.js, connected to a
// bash shell inside the server's container through a WebSocket (see
// lib/session.ts). It prints a banner that says where the shell runs and how
// the session can end, passes keystrokes and resizes to the shell, and draws
// the shell's output. When the session ends, Enter starts a new one. Its
// screen is kept when the page is left, and redrawn when it is opened again in
// the same browser tab, above a new session (see lib/screen.ts). The
// component is styled to resemble a classic terminal window and is responsive
// to container size changes.
// ----------------------------------------------------------------------------
import { useEffect, useRef, useState } from "react";
import { FitAddon } from "@xterm/addon-fit";
import { SerializeAddon } from "@xterm/addon-serialize";
import { Terminal } from "@xterm/xterm";
import "@xterm/xterm/css/xterm.css";
import "@/components/Terminal/styles.css";
import { gettext } from "@smarter/common";
import type { SessionContext } from "@smarter/common";

import { banner, ended, restored } from "@/lib/banner";
import { MAX_SAVED_LINES, loadScreen, saveScreen } from "@/lib/screen";
import { TerminalSession } from "@/lib/session";
import type { SessionInfo } from "@/lib/session";

const terminalTheme = {
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
};
const terminalConfig = {
  cursorBlink: true,
  fontFamily: '"JetBrains Mono", "SFMono-Regular", Menlo, monospace',
  fontSize: 13,
  lineHeight: 1.2,
  scrollback: 10000,
  theme: terminalTheme,
};

type Status = "connecting" | "connected" | "ended";

interface TerminalEmulatorProps {
  sessionContext: SessionContext;
}

function TerminalEmulator({ sessionContext }: TerminalEmulatorProps) {
  const [status, setStatus] = useState<Status>("connecting");
  const [info, setInfo] = useState<SessionInfo | null>(null);
  const terminalContainerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!terminalContainerRef.current) {
      return;
    }

    const term = new Terminal(terminalConfig);
    const fitAddon = new FitAddon();
    const serializeAddon = new SerializeAddon();
    term.loadAddon(fitAddon);
    term.loadAddon(serializeAddon);
    term.open(terminalContainerRef.current);

    // the screen from before the page was left: its shell has ended.
    const screen = loadScreen();
    if (screen) {
      term.write(screen);
      term.write(restored());
    }
    // a full screen program's alternate screen, and modes such as mouse tracking, are not kept,
    // so that the redrawn screen is the plain terminal.
    const keepScreen = () =>
      saveScreen(serializeAddon.serialize({ scrollback: MAX_SAVED_LINES, excludeAltBuffer: true, excludeModes: true }));
    window.addEventListener("pagehide", keepScreen);

    let session: TerminalSession | null = null;
    let running = false;

    const connect = () => {
      setStatus("connecting");
      setInfo(null);
      running = true;
      session = new TerminalSession(sessionContext, {
        onOpen: (sessionInfo) => {
          setInfo(sessionInfo);
          setStatus("connected");
          term.write(banner(sessionInfo));
        },
        onOutput: (data) => term.write(data),
        onExit: (reason, code) => {
          running = false;
          setStatus("ended");
          term.write(ended(reason, code));
        },
      });
      void session.connect(term.cols, term.rows);
    };

    const onData = term.onData((data) => {
      if (running) {
        session?.sendInput(data);
      } else if (data.includes("\r")) {
        connect();
      }
    });
    const onResize = term.onResize(({ cols, rows }) => session?.resize(cols, rows));

    const fit = () => fitAddon.fit();
    const resizeObserver = new ResizeObserver(fit);
    resizeObserver.observe(terminalContainerRef.current);
    window.addEventListener("resize", fit);

    // connect at the terminal's fitted size, after the browser's layout.
    const rafId = requestAnimationFrame(() => {
      fit();
      term.focus();
      connect();
    });

    return () => {
      cancelAnimationFrame(rafId);
      window.removeEventListener("resize", fit);
      window.removeEventListener("pagehide", keepScreen);
      keepScreen();
      resizeObserver.disconnect();
      onData.dispose();
      onResize.dispose();
      session?.close();
      term.dispose();
    };
  }, [sessionContext]);

  const statusText = {
    connecting: gettext("connecting"),
    connected: gettext("connected"),
    ended: gettext("disconnected"),
  }[status];

  return (
    <section className="terminal-window" aria-label={gettext("Terminal")}>
      <div className="terminal-window__header">
        <div className="terminal-window__controls" aria-hidden="true">
          <span className="terminal-window__dot terminal-window__dot--close" />
          <span className="terminal-window__dot terminal-window__dot--minimize" />
          <span className="terminal-window__dot terminal-window__dot--maximize" />
        </div>
        <div className="terminal-window__title">{info ? `${info.user}@${info.hostname}` : gettext("terminal")}</div>
        <div className={`terminal-window__status ${status === "connected" ? "is-online" : "is-offline"}`} role="status">
          {statusText}
        </div>
      </div>

      <div className="terminal-window__body">
        <div ref={terminalContainerRef} className="terminal-window__xterm" />
      </div>
    </section>
  );
}

export default TerminalEmulator;

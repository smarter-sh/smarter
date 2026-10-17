/**
 * A terminal session: a bash shell inside the server's container, over a WebSocket.
 *
 * connect() POSTs to the ticket api (the root element's smarter-api-path) for a single use
 * ticket, then opens the WebSocket that the api names, with the ticket and the terminal's size.
 * The server sends the shell's output as binary messages, and its session and exit messages as
 * JSON text. Input and resizes are sent as JSON text. See
 * smarter.apps.dashboard.views.terminal_emulator.api.messages.
 */
import { fetchDjangoUrl } from "@smarter/common";
import type { SessionContext } from "@smarter/common";

/** Where the shell runs, and how long the session can last: the server's session message. */
export interface SessionInfo {
  hostname: string;
  user: string;
  command: string;
  pid: number;
  idle_timeout: number;
  max_duration: number;
}

/**
 * Why a session ended. The server reports the first four. "refused": the ticket api or the
 * WebSocket refused the connection. "disconnected": the connection closed without an exit message,
 * e.g. because the server restarted, or the network dropped.
 */
export type ExitReason = "exited" | "idle" | "expired" | "failed" | "refused" | "disconnected";

export interface SessionHandlers {
  /** The shell started. */
  onOpen: (info: SessionInfo) => void;
  /** The shell's output, as raw bytes. */
  onOutput: (data: Uint8Array) => void;
  /** The session ended. Called once. */
  onExit: (reason: ExitReason, code: number | null) => void;
}

interface Ticket {
  ticket: string;
  url: string;
}

type ServerMessage = ({ type: "session" } & SessionInfo) | { type: "exit"; reason: ExitReason; code: number | null };

/** The WebSocket's url: the page's host, ws or wss as the page is http or https, the ticket and the size. */
export function websocketUrl(path: string, ticket: string, cols: number, rows: number, location: Location): string {
  const url = new URL(path, location.href);
  url.protocol = location.protocol === "https:" ? "wss:" : "ws:";
  url.search = new URLSearchParams({ ticket, cols: String(cols), rows: String(rows) }).toString();
  return url.toString();
}

export class TerminalSession {
  private socket: WebSocket | null = null;
  private ended = false;
  private started = false;

  constructor(
    private readonly sessionContext: SessionContext,
    private readonly handlers: SessionHandlers,
  ) {}

  /** Request a ticket, and open the WebSocket. A failure ends the session as "refused". */
  async connect(cols: number, rows: number): Promise<void> {
    let ticket: Ticket;
    try {
      const response = await fetchDjangoUrl(this.sessionContext, this.sessionContext.ApiUrl, "{}");
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      ticket = (await response.json()) as Ticket;
    } catch (error) {
      console.error("TerminalSession.connect() could not get a ticket:", error);
      this.end("refused", null);
      return;
    }
    if (this.ended) return;
    const socket = new WebSocket(websocketUrl(ticket.url, ticket.ticket, cols, rows, window.location));
    socket.binaryType = "arraybuffer";
    socket.onmessage = (event: MessageEvent) => this.receive(event.data);
    socket.onclose = () => this.end(this.started ? "disconnected" : "refused", null);
    this.socket = socket;
  }

  private receive(data: unknown) {
    // binaryType is "arraybuffer": text is a JSON message, anything else is output.
    if (typeof data !== "string") {
      this.handlers.onOutput(new Uint8Array(data as ArrayBuffer));
      return;
    }
    const message = JSON.parse(String(data)) as ServerMessage;
    if (message.type === "session") {
      this.started = true;
      this.handlers.onOpen(message);
    } else if (message.type === "exit") {
      this.end(message.reason, message.code);
    }
  }

  private end(reason: ExitReason, code: number | null) {
    if (this.ended) return;
    this.ended = true;
    this.handlers.onExit(reason, code);
    this.socket?.close();
  }

  private send(message: object) {
    if (this.socket?.readyState === WebSocket.OPEN) this.socket.send(JSON.stringify(message));
  }

  /** Send keystrokes, or pasted text, to the shell. */
  sendInput(data: string) {
    this.send({ type: "input", data });
  }

  /** Tell the shell that the terminal changed size. */
  resize(cols: number, rows: number) {
    this.send({ type: "resize", cols, rows });
  }

  /** End the session from the browser, e.g. when the page unmounts. Calls no handler. */
  close() {
    this.ended = true;
    this.socket?.close();
  }
}

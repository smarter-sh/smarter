/**
 * Test doubles for what jsdom lacks, or tests drive by hand: the terminal's WebSocket, and the
 * canvas that xterm.js draws on. Tests install them with installFakes(), drive the WebSocket
 * through FakeWebSocket.latest(), and type with FakeTerminal.latest().type().
 */
import { vi } from "vitest";

type Listener<T> = (event: T) => void;

export class FakeWebSocket {
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSING = 2;
  static readonly CLOSED = 3;
  static instances: FakeWebSocket[] = [];
  static latest(): FakeWebSocket {
    return FakeWebSocket.instances[FakeWebSocket.instances.length - 1];
  }

  readyState = FakeWebSocket.CONNECTING;
  binaryType = "blob";
  sent: string[] = [];
  onmessage: Listener<MessageEvent> | null = null;
  onclose: Listener<CloseEvent> | null = null;

  constructor(public url: string) {
    FakeWebSocket.instances.push(this);
  }

  send(data: string) {
    this.sent.push(data);
  }

  close() {
    if (this.readyState === FakeWebSocket.CLOSED) return;
    this.readyState = FakeWebSocket.CLOSED;
    this.onclose?.(new CloseEvent("close"));
  }

  /** The messages that were sent, parsed. */
  messages(): { type: string; [key: string]: unknown }[] {
    return this.sent.map((data) => JSON.parse(data));
  }

  /** The server accepts the connection. */
  open() {
    this.readyState = FakeWebSocket.OPEN;
  }

  /** The server sends a JSON text message. */
  emitJson(message: unknown) {
    this.onmessage?.(new MessageEvent("message", { data: JSON.stringify(message) }));
  }

  /** The server sends the shell's output, as a binary message. */
  emitOutput(text: string) {
    this.onmessage?.(new MessageEvent("message", { data: new TextEncoder().encode(text).buffer }));
  }

  /** The server, or the network, closes the connection. */
  drop() {
    this.close();
  }
}

/** What the terminal wrote to its xterm.js Terminal, as text. */
export const written: string[] = [];

const decoder = new TextDecoder();

/** A stand-in for xterm.js's Terminal, which records what is written to it. */
export class FakeTerminal {
  static instances: FakeTerminal[] = [];
  static latest(): FakeTerminal {
    return FakeTerminal.instances[FakeTerminal.instances.length - 1];
  }

  cols = 120;
  rows = 40;
  focused = false;
  disposed = false;
  private dataListeners: Listener<string>[] = [];
  private resizeListeners: Listener<{ cols: number; rows: number }>[] = [];

  constructor() {
    FakeTerminal.instances.push(this);
  }

  loadAddon() {}
  open() {}
  focus() {
    this.focused = true;
  }
  dispose() {
    this.disposed = true;
  }
  write(data: string | Uint8Array) {
    written.push(typeof data === "string" ? data : decoder.decode(data));
  }
  onData(listener: Listener<string>) {
    this.dataListeners.push(listener);
    return { dispose: () => (this.dataListeners = this.dataListeners.filter((l) => l !== listener)) };
  }
  onResize(listener: Listener<{ cols: number; rows: number }>) {
    this.resizeListeners.push(listener);
    return { dispose: () => (this.resizeListeners = this.resizeListeners.filter((l) => l !== listener)) };
  }

  /** The user types, or pastes, into the terminal. */
  type(data: string) {
    this.dataListeners.forEach((listener) => listener(data));
  }

  /** The terminal is fitted to a new size. */
  resize(cols: number, rows: number) {
    this.cols = cols;
    this.rows = rows;
    this.resizeListeners.forEach((listener) => listener({ cols, rows }));
  }
}

export class FakeFitAddon {
  fit() {}
}

/** A stand-in for xterm.js's SerializeAddon: the screen is what was written to the terminal. */
export class FakeSerializeAddon {
  static options: unknown[] = [];
  serialize(options?: unknown) {
    FakeSerializeAddon.options.push(options);
    return written.join("");
  }
}

class FakeResizeObserver {
  observe() {}
  disconnect() {}
}

/** Install the fakes of the globals. xterm.js's modules are mocked with vi.mock, in each test file. */
export function installFakes() {
  FakeWebSocket.instances = [];
  FakeTerminal.instances = [];
  FakeSerializeAddon.options = [];
  written.length = 0;
  vi.stubGlobal("WebSocket", FakeWebSocket);
  vi.stubGlobal("ResizeObserver", FakeResizeObserver);
  // run the component's first fit, and its connection, at once.
  vi.stubGlobal("requestAnimationFrame", (callback: FrameRequestCallback) => {
    callback(0);
    return 0;
  });
  vi.stubGlobal("cancelAnimationFrame", () => {});
}

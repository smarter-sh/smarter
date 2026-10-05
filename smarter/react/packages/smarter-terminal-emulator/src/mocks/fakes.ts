/**
 * Test doubles for what jsdom lacks: EventSource, the log stream's transport, and the canvas
 * that xterm.js draws on. Tests install them with installFakes(), and drive the log stream
 * through FakeEventSource.latest().
 */
import { vi } from "vitest";

export class FakeEventSource {
  static instances: FakeEventSource[] = [];
  static latest(): FakeEventSource {
    return FakeEventSource.instances[FakeEventSource.instances.length - 1];
  }

  onopen: (() => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: (() => void) | null = null;
  closed = false;
  private listeners: Record<string, ((event: MessageEvent) => void)[]> = {};

  constructor(public url: string) {
    FakeEventSource.instances.push(this);
  }

  addEventListener(type: string, listener: (event: MessageEvent) => void) {
    (this.listeners[type] ??= []).push(listener);
  }

  close() {
    this.closed = true;
  }

  /** The server accepts the connection. */
  open() {
    this.onopen?.();
  }

  /** The server sends an event: a named one, e.g. "bulk", or else a message. */
  emit(data: unknown, type?: string) {
    const event = new MessageEvent(type ?? "message", { data: typeof data === "string" ? data : JSON.stringify(data) });
    if (type) this.listeners[type]?.forEach((listener) => listener(event));
    else this.onmessage?.(event);
  }

  /** The connection fails. */
  fail() {
    this.onerror?.();
  }
}

/** What the terminal wrote to its xterm.js Terminal. */
export const written: string[] = [];

/** A stand-in for xterm.js's Terminal, which records what is written to it. */
export class FakeTerminal {
  loadAddon() {}
  open() {}
  dispose() {}
  write(data: string) {
    written.push(data);
  }
  writeln(data: string) {
    written.push(`${data}\n`);
  }
}

export class FakeFitAddon {
  fit() {}
}

class FakeResizeObserver {
  observe() {}
  disconnect() {}
}

/** Install the fakes of the globals. xterm.js's modules are mocked with vi.mock, in each test file. */
export function installFakes() {
  FakeEventSource.instances = [];
  written.length = 0;
  vi.stubGlobal("EventSource", FakeEventSource);
  vi.stubGlobal("ResizeObserver", FakeResizeObserver);
}

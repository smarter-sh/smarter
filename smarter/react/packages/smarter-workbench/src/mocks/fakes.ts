/**
 * A test double for what jsdom lacks: EventSource, which the Console's log stream uses. Tests
 * install it with installFakes(), and drive the log stream through FakeEventSource.latest().
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

  constructor(
    public url: string,
    public init?: EventSourceInit,
  ) {
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

export function installFakes() {
  FakeEventSource.instances = [];
  vi.stubGlobal("EventSource", FakeEventSource);
}

/**
 * Render every story in this package as a test. See test/stories.ts in the workspace. jsdom has
 * no EventSource, nor the canvas that xterm.js draws on, so they are replaced by fakes.
 */
import { beforeEach, vi } from "vitest";

import { installFakes } from "@/mocks/fakes";
import { testStories } from "@test/stories";

// MSW's sse() handlers, which the stories import, require an EventSource when they are created.
vi.hoisted(() => {
  globalThis.EventSource ??= class {} as unknown as typeof EventSource;
});
vi.mock("@xterm/xterm", async () => ({ Terminal: (await import("@/mocks/fakes")).FakeTerminal }));
vi.mock("@xterm/addon-fit", async () => ({ FitAddon: (await import("@/mocks/fakes")).FakeFitAddon }));
vi.mock("@xterm/xterm/css/xterm.css", () => ({}));

beforeEach(() => {
  installFakes();
});

testStories(import.meta.glob("./**/*.stories.tsx", { eager: true }));

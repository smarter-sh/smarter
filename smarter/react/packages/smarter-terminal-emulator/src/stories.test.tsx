/**
 * Render every story in this package as a test. See test/stories.ts in the workspace. The
 * WebSocket, and the canvas that xterm.js draws on and its addons, are replaced by fakes.
 */
import { beforeEach, vi } from "vitest";

import { installFakes } from "@/mocks/fakes";
import { testStories } from "@test/stories";

vi.mock("@xterm/xterm", async () => ({ Terminal: (await import("@/mocks/fakes")).FakeTerminal }));
vi.mock("@xterm/addon-fit", async () => ({ FitAddon: (await import("@/mocks/fakes")).FakeFitAddon }));
vi.mock("@xterm/addon-serialize", async () => ({
  SerializeAddon: (await import("@/mocks/fakes")).FakeSerializeAddon,
}));
vi.mock("@xterm/xterm/css/xterm.css", () => ({}));

beforeEach(() => {
  installFakes();
});

testStories(import.meta.glob("./**/*.stories.tsx", { eager: true }));

/**
 * Render every story in this package as a test. See test/stories.ts in the workspace. Monaco,
 * which jsdom cannot run, is replaced by a textarea.
 */
import { vi } from "vitest";

import { testStories } from "@test/stories";

vi.mock("@monaco-editor/react", async () => await import("@/mocks/MonacoEditor"));

testStories(import.meta.glob("./**/*.stories.tsx", { eager: true }));

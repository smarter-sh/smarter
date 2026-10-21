/** Render every story in this package as a test. See test/stories.ts. */
import { vi } from "vitest";

import { testStories } from "@test/stories";

// jsdom can't lay out mermaid's svg. In Storybook, the WithDiagram story uses the real mermaid.
vi.mock("mermaid", async () => ({ default: (await import("@/mocks/mermaid")).fakeMermaid }));

testStories(import.meta.glob("./**/*.stories.tsx", { eager: true }));

/**
 * Render every story of a package as a test, so that the stories stay current: a story that no
 * longer renders, e.g. because a component's props changed, fails the package's tests.
 *
 * Each package calls it from src/stories.test.tsx:
 *
 *     import { testStories } from "@test/stories";
 *     testStories(import.meta.glob("./**\/*.stories.tsx", { eager: true }));
 *
 * A story's play function, if any, runs too, and its parameters.msw.handlers answer its API
 * requests, as they do in Storybook (see storybook/preview.ts).
 */
import { composeStories } from "@storybook/react-vite";
import type { RequestHandler } from "msw";
import { describe, it } from "vitest";

import { server } from "./server";

type StoriesModule = Parameters<typeof composeStories>[0];

/** What testStories needs of a composed story. */
type ComposedStory = {
  parameters?: { msw?: { handlers?: RequestHandler[] } };
  run: () => Promise<void>;
};

export function testStories(modules: Record<string, unknown>) {
  for (const [file, module] of Object.entries(modules)) {
    const stories = composeStories(module as StoriesModule);
    describe(file, () => {
      for (const [name, Story] of Object.entries(stories) as [string, ComposedStory][]) {
        it(`renders the ${name} story`, async () => {
          server.use(...(Story.parameters?.msw?.handlers ?? []));
          await Story.run();
        });
      }
    });
  }
}

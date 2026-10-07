/**
 * Storybook parameters shared by Storybook (storybook/preview.ts) and by the Vitest tests that
 * render every story (test/stories.ts).
 */
import type { Parameters } from "@storybook/react-vite";

export const sharedParameters: Parameters = {
  layout: "padded",
  controls: {
    matchers: {
      color: /(background|color)$/i,
      date: /(Date|At)$/i,
    },
  },
  a11y: {
    // 'todo' shows accessibility violations in Storybook's test UI, without failing.
    // Change this to 'error' to fail on violations.
    test: "todo",
  },
};

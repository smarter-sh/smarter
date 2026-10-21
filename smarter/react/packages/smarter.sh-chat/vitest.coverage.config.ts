/**
 * The tests with a coverage report: `make coverage`, or `npm run coverage`. CI uploads its
 * coverage/lcov.info to Codecov.
 *
 * Coverage is configured here rather than in vitest.config.ts, which the Smarter React workspace
 * runs as one of its projects, and a project cannot configure coverage: the workspace's
 * vitest.config.ts does, for all of its packages.
 */
import { defineConfig, mergeConfig } from "vitest/config";

import project from "./vitest.config";

export default mergeConfig(
  project,
  defineConfig({
    test: {
      coverage: {
        provider: "v8",
        include: ["src/**/*.{ts,tsx}"],
        exclude: ["**/*.stories.tsx", "**/*.test.{ts,tsx}", "**/mocks/**", "src/main.tsx", "**/*.d.ts"],
        reporter: ["text-summary", "html", "lcov"],
        reportsDirectory: "coverage",
      },
    },
  }),
);

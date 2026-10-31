/**
 * Run every package's tests: `npm test`, or `npm run coverage` for a coverage report, in
 * smarter/react. See vitest.shared.ts.
 */
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    projects: ["packages/*/vitest.config.ts", "i18n/vitest.config.ts"],
    coverage: {
      provider: "v8",
      include: ["packages/*/src/**/*.{ts,tsx}", "i18n/*.ts"],
      exclude: ["**/*.stories.tsx", "**/*.test.{ts,tsx}", "**/*.config.ts", "**/mocks/**", "**/main.tsx", "**/*.d.ts"],
      // json-summary: coverage/coverage-summary.json, whose total the Tests workflow posts to Slack.
      reporter: ["text-summary", "html", "lcov", "json-summary"],
      reportsDirectory: "coverage",
    },
  },
});

/**
 * Run every package's tests: `npm test`, or `npm run coverage` for a coverage report, in
 * smarter/react. See vitest.shared.ts.
 */
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    projects: ["packages/*/vitest.config.ts"],
    coverage: {
      provider: "v8",
      include: ["packages/*/src/**/*.{ts,tsx}"],
      exclude: ["**/*.stories.tsx", "**/*.test.{ts,tsx}", "**/mocks/**", "**/main.tsx", "**/*.d.ts"],
      reporter: ["text-summary", "html", "lcov"],
      reportsDirectory: "coverage",
    },
  },
});

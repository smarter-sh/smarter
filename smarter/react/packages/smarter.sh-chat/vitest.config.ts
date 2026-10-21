/**
 * Tests for Smarter Chat: `make test`, or `npm test`. See vitest.coverage.config.ts for the coverage
 * report.
 *
 * This is self-contained, so that the tests run both in a plain clone of this repository and inside
 * the npm workspace of https://github.com/smarter-sh/smarter, whose vitest.config.ts runs it as one
 * of its projects, configured the same way as the workspace's other packages (see vitest.shared.ts
 * there):
 *
 * - Tests are src/**\/*.test.{ts,tsx}, run in jsdom, a simulated browser.
 * - test/setup.ts adds jest-dom's matchers, and MSW, which answers the tests' API requests.
 * - @/ resolves to src/, as in vite.config.ts, and @test/ to test/.
 */
import path from "node:path";
import react from "@vitejs/plugin-react";
import { defineProject } from "vitest/config";

const PACKAGE_DIR = import.meta.dirname;

// Tests run React's development build, which has act() and its warnings. Vitest only sets
// NODE_ENV=test when it is unset, and a shell may export NODE_ENV=production for builds.
process.env.NODE_ENV = "test";
// Dates, times and amounts are formatted the same way on every machine.
process.env.TZ = "UTC";
process.env.LANG = "en_US.UTF-8";

export default defineProject({
  plugins: [react()],
  resolve: {
    alias: {
      "@test": path.join(PACKAGE_DIR, "test"),
      "@": path.join(PACKAGE_DIR, "src"),
    },
  },
  test: {
    name: path.basename(PACKAGE_DIR),
    root: PACKAGE_DIR,
    environment: "jsdom",
    environmentOptions: { jsdom: { url: "http://localhost:9357/" } },
    setupFiles: [path.join(PACKAGE_DIR, "test", "setup.ts")],
    include: ["src/**/*.test.{ts,tsx}"],
    restoreMocks: true,
  },
});

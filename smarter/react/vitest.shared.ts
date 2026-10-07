/**
 * Shared Vitest configuration for every package in this workspace.
 *
 * Each package's vitest.config.ts calls smarterVitestProject(import.meta.dirname). The workspace's
 * vitest.config.ts runs all of the packages' tests together: `npm test` in smarter/react.
 *
 * - Tests are the package's src/**\/*.test.{ts,tsx} files, run in jsdom, a simulated browser.
 * - test/setup.ts adds jest-dom's matchers, and MSW, which answers the tests' API requests.
 * - @smarter/common resolves to its TypeScript source, so that tests never depend on a stale build.
 * - @/ resolves to the package's src/, as in its vite.config.ts, and @test/ to this test/ folder.
 */
import path from "node:path";
import react from "@vitejs/plugin-react";
import { defineProject } from "vitest/config";

const WORKSPACE = import.meta.dirname;

// Tests run React's development build, which has act() and its warnings. Vitest only sets
// NODE_ENV=test when it is unset, and a shell may export NODE_ENV=production for builds.
process.env.NODE_ENV = "test";
// Dates, times and amounts are formatted the same way on every machine.
process.env.TZ = "UTC";
process.env.LANG = "en_US.UTF-8";

export function smarterVitestProject(packageDir: string) {
  return defineProject({
    plugins: [react()],
    resolve: {
      alias: {
        "@smarter/common": path.join(WORKSPACE, "packages", "smarter-common", "src", "index.tsx"),
        "@test": path.join(WORKSPACE, "test"),
        "@": path.join(packageDir, "src"),
      },
    },
    test: {
      name: path.basename(packageDir),
      root: packageDir,
      environment: "jsdom",
      environmentOptions: { jsdom: { url: "http://localhost:9357/" } },
      setupFiles: [path.join(WORKSPACE, "test", "setup.ts")],
      include: ["src/**/*.test.{ts,tsx}"],
      restoreMocks: true,
    },
  });
}

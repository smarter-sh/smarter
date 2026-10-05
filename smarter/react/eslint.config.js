/**
 * Shared ESLint configuration for every package in this workspace. Each package's
 * eslint.config.js re-exports it, so `npm run lint` lints the same way in each package, and in
 * smarter/react, where it lints them all. pre-commit runs it on the files of each commit.
 *
 * - TypeScript, React hooks and React Refresh rules for all source files.
 * - jsx-a11y: accessibility rules for JSX.
 * - Storybook's rules for stories.
 * - Testing Library, jest-dom and Vitest rules for tests.
 * - eslint-config-prettier, last: formatting is Prettier's job, not ESLint's.
 */
import js from "@eslint/js";
import vitest from "@vitest/eslint-plugin";
import prettier from "eslint-config-prettier";
import jestDom from "eslint-plugin-jest-dom";
import jsxA11y from "eslint-plugin-jsx-a11y";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import storybook from "eslint-plugin-storybook";
import testingLibrary from "eslint-plugin-testing-library";
import { defineConfig, globalIgnores } from "eslint/config";
import globals from "globals";
import tseslint from "typescript-eslint";

const TESTS = ["**/*.test.{ts,tsx}", "**/test/**/*.{ts,tsx}"];

export default defineConfig([
  globalIgnores(["**/dist", "**/storybook-static", "**/coverage", "**/node_modules", "storybook/public"]),
  {
    files: ["**/*.{ts,tsx}"],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
      jsxA11y.flatConfigs.recommended,
    ],
    languageOptions: {
      globals: globals.browser,
    },
    rules: {
      // unused variables are errors, except those named _, e.g. the ignored half of a [key, value] pair.
      "@typescript-eslint/no-unused-vars": ["error", { argsIgnorePattern: "^_", varsIgnorePattern: "^_" }],
    },
  },
  {
    // configuration files run in Node.
    files: ["**/*.config.{js,ts}", "**/.storybook/*.ts", "storybook/*.ts", "vitest.shared.ts"],
    languageOptions: {
      globals: globals.node,
    },
  },
  ...storybook.configs["flat/recommended"],
  {
    // stories and tests export or define more than components.
    files: ["**/*.stories.tsx", ...TESTS, "**/mocks/**/*.{ts,tsx}"],
    rules: {
      "react-refresh/only-export-components": "off",
    },
  },
  {
    // a library, not an app: its index files re-export its api, and it has no hot reloading.
    // (Inside the package, packages/smarter-common/eslint.config.js does the same.)
    files: ["packages/smarter-common/src/**/*.{ts,tsx}"],
    rules: {
      "react-refresh/only-export-components": "off",
    },
  },
  {
    files: TESTS,
    extends: [testingLibrary.configs["flat/react"], jestDom.configs["flat/recommended"], vitest.configs.recommended],
  },
  {
    files: ["test/setup.ts"],
    rules: {
      // Vitest's globals are off, so Testing Library's automatic cleanup is not registered.
      "testing-library/no-manual-cleanup": "off",
    },
  },
  {
    files: ["test/stories.ts"],
    rules: {
      // each story is a test, named after it, whose assertions are the story's play function.
      "vitest/valid-title": "off",
      "vitest/expect-expect": "off",
    },
  },
  prettier,
]);

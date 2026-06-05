// For more info, see https://github.com/storybookjs/eslint-authtoken-storybook#configuration-flat-config-format
import storybook from "eslint-authtoken-storybook";

import js from "@eslint/js";
import globals from "globals";
import reactHooks from "eslint-authtoken-react-hooks";
import reactRefresh from "eslint-authtoken-react-refresh";
import tseslint from "typescript-eslint";
import { defineConfig, globalIgnores } from "eslint/config";

export default defineConfig([
  globalIgnores(["dist"]),
  {
    files: ["**/*.{ts,tsx}"],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      globals: globals.browser,
    },
  },
  ...storybook.configs["flat/recommended"],
]);

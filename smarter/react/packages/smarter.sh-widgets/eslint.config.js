// The workspace's shared ESLint configuration. See eslint.config.js in smarter/react.
import shared from "../../eslint.config.js";

export default [
  ...shared,
  {
    // a library, not an app: its index files re-export its api, and it has no hot reloading.
    files: ["src/**/*.{ts,tsx}"],
    rules: {
      "react-refresh/only-export-components": "off",
    },
  },
];

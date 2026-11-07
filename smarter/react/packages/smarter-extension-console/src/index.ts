/**
 * The Extensions console, as a component, for the single-page console (@smarter/console), which renders it at
 * /extensions and /extensions/<slug>. main.tsx is the package's development page only.
 *
 * The package's source uses relative imports, so that another package's build can import it.
 */
export { default as ExtensionConsole } from "./App";
export type { ConsoleContext as ExtensionConsoleContext } from "./lib/types";

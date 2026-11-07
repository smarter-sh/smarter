/**
 * The Prompt Engineer's Workbench, as a component, for the single-page console (@smarter/console), which renders it
 * at /workbench/llm-clients/:id/prompt. main.tsx is the package's development page only.
 *
 * The package's source uses relative imports, so that another package's build can import it.
 */
export { default as Workbench } from "./App";
export type { AppProps as WorkbenchProps } from "./App";
export type { WorkbenchConfig } from "./lib/types";

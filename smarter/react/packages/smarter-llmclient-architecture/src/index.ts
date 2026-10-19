/**
 * An LLMClient's architecture, as a component, for the web console's other React apps: the Prompt Engineer's
 * Workbench (@smarter/workbench) renders it in its Console's Architecture tab. main.tsx is the package's
 * development page only.
 *
 * The package's source uses relative imports, so that another package's build can import it.
 */
export { default as LLMClientArchitecture } from "./App";
export type { ArchitectureProps } from "./App";
export type { SAMDependencyTreeNode } from "./lib/types";

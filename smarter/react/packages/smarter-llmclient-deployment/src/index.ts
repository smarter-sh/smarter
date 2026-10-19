/**
 * The deployment page, as a component, for the web console's other React apps: the Prompt Engineer's Workbench
 * (@smarter/workbench) renders it in its Console's Deployment tab, in its workbench mode. The page at a deployed
 * LLMClient's url is main.tsx.
 *
 * The package's source uses relative imports, so that another package's build can import it.
 */
export { default as DeploymentPage } from "./App";
export type { DeploymentContext, LLMClientDeploymentPage } from "./lib/types";

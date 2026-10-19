/**
 * Reads the app's context from its root element, and from the json_script that it names, which Django renders:
 * templates/llmclient/endpoints.html, the page at a deployed LLMClient's url.
 */
import type { DeploymentContext, LLMClientDeploymentPage } from "./types";

/** The root element of the page. */
export const ROOT_ID = "smarter-llmclient-deployment-root";

/**
 * Return the app's context, from its root element's attributes and its data.
 *
 * The page at a deployed LLMClient's url has no session, and no actions: the Prompt Engineer's Workbench, which
 * manages the LLMClient's api key, passes its own session to the component.
 *
 * @param rootEl - The root element.
 * @returns The context.
 * @throws If the data is missing.
 */
export function readContext(rootEl: HTMLElement): DeploymentContext {
  const dataId = rootEl.getAttribute("smarter-deployment-data-id");
  if (!dataId)
    throw new Error("The LLMClient deployment app's root element has no smarter-deployment-data-id attribute.");
  const dataEl = rootEl.ownerDocument.getElementById(dataId);
  if (!dataEl) throw new Error(`The LLMClient deployment app's data element ${dataId} was not found.`);
  const page = JSON.parse(dataEl.textContent || "null") as LLMClientDeploymentPage | null;
  if (!page) throw new Error(`The LLMClient deployment app's data element ${dataId} is empty.`);
  return { page, session: null };
}

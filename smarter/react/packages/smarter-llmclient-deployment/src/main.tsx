/**
 * Main entry point of the LLMClient deployment app: the page at a deployed LLMClient's url, which Django renders
 * in templates/llmclient/endpoints.html, with its data in a json_script. See
 * smarter.apps.llmclient.views.endpoints. The Prompt Engineer's Workbench renders the same page, in its
 * Deployment tab, with the package's component (src/index.ts).
 */
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App";
import { loggerPrefix } from "./lib/const";
import { readContext, ROOT_ID } from "./lib/session";

const rootEl = document.getElementById(ROOT_ID);
if (!rootEl) throw new Error("The LLMClient deployment app's root element was not found.");

const context = readContext(rootEl);
console.debug(`${loggerPrefix} context:`, context);
createRoot(rootEl).render(
  <StrictMode>
    <App context={context} />
  </StrictMode>,
);

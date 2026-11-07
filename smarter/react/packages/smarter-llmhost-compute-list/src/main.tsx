/**
 * The development page of the LLM Host Compute list (`npm run dev`), with the example session context of
 * src/mocks/fixtures.ts. It calls the Django dev server's list api, through vite.config.ts's proxy, as the signed-in
 * user of localhost:9357. In the web console, @smarter/console renders the package's component (src/index.ts).
 */
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App";
import { sessionContext } from "./mocks/fixtures";

const rootEl = document.getElementById("smarter-llmhost-compute-list-root");
if (!rootEl) throw new Error("The LLM Host Compute list's root element was not found.");

createRoot(rootEl).render(
  <StrictMode>
    <App sessionContext={sessionContext} />
  </StrictMode>,
);

/**
 * The development page of the LLMClient architecture (`npm run dev`), which draws an example architecture of
 * src/mocks/fixtures.ts: an LLMClient that uses nothing, so that every next step shows. In the web console, the
 * Prompt Engineer's Workbench renders the package's component (src/index.ts) in its Console's Architecture tab.
 */
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App";
import { leafArchitecture } from "./mocks/fixtures";

const rootEl = document.getElementById("smarter-llmclient-architecture-root");
if (!rootEl) throw new Error("The LLMClient architecture's root element was not found.");

createRoot(rootEl).render(
  <StrictMode>
    <App architecture={leafArchitecture} onReload={() => window.location.reload()} />
  </StrictMode>,
);

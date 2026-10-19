/**
 * The development page of the LLMClient architecture (`npm run dev`), which draws the example tree of
 * src/mocks/fixtures.ts. In the web console, the Prompt Engineer's Workbench renders the package's component
 * (src/index.ts) in its Console's Architecture tab.
 */
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App";
import { stackademyTree } from "./mocks/fixtures";

const rootEl = document.getElementById("smarter-llmclient-architecture-root");
if (!rootEl) throw new Error("The LLMClient architecture's root element was not found.");

createRoot(rootEl).render(
  <StrictMode>
    <App tree={stackademyTree} onReload={() => window.location.reload()} />
  </StrictMode>,
);

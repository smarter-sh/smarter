/**
 * The development page of the Prompt Engineer's Workbench (`npm run dev`), with the example configuration of
 * src/mocks/fixtures.ts. It calls the Django dev server's api, through vite.config.ts's proxy, as the signed-in user of
 * localhost:9357: replace the fixtures' hashed id with one of your LLMClients'. In the web console, @smarter/console
 * renders the package's component (src/index.ts).
 */
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App";
import { workbench } from "./mocks/fixtures";

const rootEl = document.getElementById("smarter-workbench-root");
if (!rootEl) throw new Error("The workbench's root element was not found.");

createRoot(rootEl).render(
  <StrictMode>
    <App workbench={workbench} onboarding={null} />
  </StrictMode>,
);

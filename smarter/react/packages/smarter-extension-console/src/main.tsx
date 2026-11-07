/**
 * The development page of the Extensions console (`npm run dev`), with the example context of src/mocks/fixtures.ts:
 * the list, as a superuser. It calls the Django dev server's api, through vite.config.ts's proxy, as the signed-in
 * user of localhost:9357. In the web console, @smarter/console renders the package's component (src/index.ts).
 */
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App";
import { listContext } from "./mocks/fixtures";

const rootEl = document.getElementById("smarter-extension-console-root");
if (!rootEl) throw new Error("The Extensions console's root element was not found.");

createRoot(rootEl).render(
  <StrictMode>
    <App context={listContext} />
  </StrictMode>,
);

/**
 * The development page of the dashboard (`npm run dev`), with the example context of src/mocks/fixtures.ts. Its
 * widgets call the Django dev server's dashboard api, through vite.config.ts's proxy, as the signed-in user of
 * localhost:9357. In the web console, @smarter/console renders the package's component (src/index.ts).
 */
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App";
import { appContext } from "./mocks/fixtures";

const rootEl = document.getElementById("smarter-dashboard-root");
if (!rootEl) throw new Error("The dashboard's root element was not found.");

createRoot(rootEl).render(
  <StrictMode>
    <App appContext={appContext} />
  </StrictMode>,
);

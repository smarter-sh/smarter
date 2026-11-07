/**
 * The development page of the welcome dialog (`npm run dev`), with the example context of src/mocks/fixtures.ts. It calls the
 * Django dev server's api, through vite.config.ts's proxy, as the signed-in user of localhost:9357. In the web
 * console, @smarter/console renders the package's component (src/index.ts) in its frame.
 */
import { createRoot } from "react-dom/client";

import App from "./App";
import { appContext } from "./mocks/fixtures";

const rootEl = document.getElementById("smarter-welcome-root");
if (!rootEl) throw new Error("Root element not found");

createRoot(rootEl).render(<App appContext={appContext} />);

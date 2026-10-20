/**
 * Main entry point for the Did you know? note below the web console's title.
 *
 * See templates/react/didyouknow.html, which templates/dashboard/header.html includes while the
 * enable_web_console_did_you_know waffle switch is active.
 */
import { createRoot } from "react-dom/client";

import App from "./App";
import { loggerPrefix } from "./lib/version";

const rootEl = document.getElementById("smarter-didyouknow-root");
if (!rootEl) throw new Error("Root element not found");

console.debug(`${loggerPrefix} rendering the fact of the day.`);
createRoot(rootEl).render(<App />);

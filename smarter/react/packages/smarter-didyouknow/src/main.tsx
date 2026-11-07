/**
 * The development page of the Did you know? note (`npm run dev`). In the web console, @smarter/console renders the
 * package's component (its library, dist/) in its header while the session's didYouKnow flag is on.
 */
import { createRoot } from "react-dom/client";

import App from "./App";
import { loggerPrefix } from "./lib/version";

const rootEl = document.getElementById("smarter-didyouknow-root");
if (!rootEl) throw new Error("Root element not found");

console.debug(`${loggerPrefix} rendering the fact of the day.`);
createRoot(rootEl).render(<App />);

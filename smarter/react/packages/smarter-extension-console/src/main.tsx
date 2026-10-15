/**
 * Main entry point of the Smarter Extensions app. One app renders both of the web console's
 * Extensions pages, depending on the root element that the page's template provides:
 *
 * - #smarter-extension-list-root: the Extensions list, and the registry.
 * - #smarter-extension-detail-root: an extension's page.
 *
 * See smarter.apps.llmtool.extension.views and templates/react/extension-{list,detail}.html.
 */
import { createRoot } from "react-dom/client";

import App from "@/App";
import { loggerPrefix } from "@/lib/const";
import { DETAIL_ROOT_ID, LIST_ROOT_ID, readContext } from "@/lib/session";

const rootEl = document.getElementById(LIST_ROOT_ID) || document.getElementById(DETAIL_ROOT_ID);
if (!rootEl) throw new Error("The Extensions app's root element was not found.");

const context = readContext(rootEl);
console.debug(`${loggerPrefix} context:`, context);
createRoot(rootEl).render(<App context={context} />);

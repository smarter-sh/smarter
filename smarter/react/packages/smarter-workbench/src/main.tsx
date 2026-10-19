/**
 * Main entry point of the Prompt Engineer's Workbench, which Django renders in templates/react/workbench.html, with
 * its configuration in its root element's attributes. See
 * smarter.apps.prompt.views.detailviews.prompt_workbench_view.PromptWorkbenchView.
 */
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
// the chat's styles, and KaTeX's, which the chat library leaves to the page, so that its fonts are files that the
// browser downloads only when a message has math.
import "@smarter.sh/ui-chat/dist/ui-chat.css";
import "katex/dist/katex.min.css";

import App from "@/App";
import { loggerPrefix } from "@/lib/const";
import { readConfig, ROOT_ID } from "@/lib/session";
import "@/styles.css";

const rootEl = document.getElementById(ROOT_ID);
if (!rootEl) throw new Error("The workbench's root element was not found.");

const workbench = readConfig(rootEl);
console.debug(`${loggerPrefix} configuration:`, workbench);
createRoot(rootEl).render(
  <StrictMode>
    <App workbench={workbench} />
  </StrictMode>,
);

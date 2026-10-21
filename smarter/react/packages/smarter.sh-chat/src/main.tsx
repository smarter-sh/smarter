import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { loggerPrefix } from "@/const.tsx";
import type { SmarterChatProps } from "@/types";
import SmarterChat from "@/components/SmarterChat";

/*
 * The development server's page, index.html (`npm run dev`): the chat, with the props of its root element's
 * attributes. The web console's Prompt Engineer's Workbench is the platform's own app, @smarter/workbench, which
 * imports the library.
 */
const rootEl = document.getElementById("smarter-chat-root");
if (!rootEl) throw new Error("Root element not found");

const isTrue = (value: string | null) => value?.toLowerCase() === "true";

const apiUrl = rootEl.getAttribute("smarter-llmclient-api-url");
const csrfCookieName = rootEl.getAttribute("smarter-csrf-cookie-name");
const sessionCookieName = rootEl.getAttribute("smarter-session-cookie-name");
const cookieDomain = rootEl.getAttribute("smarter-cookie-domain") || window.location.hostname;
const toggleMetadata = isTrue(rootEl.getAttribute("smarter-toggle-metadata"));
const debugMode = isTrue(rootEl.getAttribute("react-debug-mode"));
const smarterRequestId = rootEl.getAttribute("smarter-request-id") || "";

if (!apiUrl) throw new Error("LLMClient API URL not found in root element attributes");
if (!csrfCookieName) throw new Error("CSRF cookie name not found in root element attributes");
if (!sessionCookieName) throw new Error("Session cookie name not found in root element attributes");
if (!smarterRequestId) throw new Error("Smarter request ID not found in root element attributes");

const props: SmarterChatProps = {
  apiUrl,
  csrfCookieName,
  sessionCookieName,
  cookieDomain,
  toggleMetadata,
  debugMode,
  smarterRequestId,
};

console.debug(`${loggerPrefix} initialized with:`, props);

createRoot(rootEl).render(
  <StrictMode>
    <SmarterChat {...props} />
  </StrictMode>,
);

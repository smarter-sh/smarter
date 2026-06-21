/**
 * Main entry point for the Smarter Connection List React application.
 * This module joins the DOM to the React component tree and provides
 * the necessary session context for API interactions.
 *
 * Steps:
 * 1. Retrieves necessary configuration from the root DOM element's attributes.
 * 2. Initializes a Django SessionContext.
 * 3. Renders the React App component into the root element.
 *
 */
import { createRoot } from "react-dom/client";
import type { SessionContext } from "@smarter/common";

import { loggerPrefix, projectName, projectVersion } from "./lib/const";
import App from "@/App";

const rootEl = document.getElementById("smarter-connection-list-root");
if (!rootEl) throw new Error("Root element not found");

const csrfCookieName = rootEl.getAttribute("django-csrf-cookie-name");
const djangoSessionCookieName = rootEl.getAttribute("django-session-cookie-name");
const cookieDomain = rootEl.getAttribute("django-cookie-domain") || window.location.hostname;
const debugMode = rootEl.getAttribute("react-debug-mode")?.toLowerCase() === "true";
const ApiUrl = rootEl.getAttribute("smarter-connection-list-api-url");
const smarterRequestId = rootEl.getAttribute("smarter-request-id") || "";

const smarterClient = projectName;
const smarterClientVersion = projectVersion;
if (!ApiUrl) throw new Error("Connection list API URL not found in root element attributes");
if (!csrfCookieName) throw new Error("CSRF token not found in root element attributes");
if (!djangoSessionCookieName) throw new Error("Django session cookie name not found in root element attributes");
if (!cookieDomain) throw new Error("Cookie domain not found in root element attributes");
if (!smarterRequestId) throw new Error("Smarter request ID not found in root element attributes");

const sessionContext: SessionContext = {
  ApiUrl,
  csrfCookieName,
  djangoSessionCookieName,
  cookieDomain,
  debugMode,
  smarterClient,
  smarterClientVersion,
  smarterRequestId,
};
console.debug(`${loggerPrefix} Session context initialized:`, sessionContext);
createRoot(rootEl).render(<App sessionContext={sessionContext} />);

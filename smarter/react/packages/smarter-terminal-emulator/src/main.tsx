import { createRoot } from "react-dom/client";

import type { SessionContext } from "@smarter/common";

import { loggerPrefix, projectName, projectVersion } from "@/const";
import App from "@/App.tsx";

const rootEl = document.getElementById("smarter-terminal-emulator-root");
if (!rootEl) throw new Error("Root element not found");

// the ticket api, whose single use ticket opens the terminal's WebSocket.
const ApiUrl = rootEl.getAttribute("smarter-api-path");
const csrfCookieName = rootEl.getAttribute("smarter-csrf-cookie-name");
const djangoSessionCookieName = rootEl.getAttribute("smarter-django-session-cookie-name");
const cookieDomain = rootEl.getAttribute("smarter-cookie-domain") || window.location.hostname;
const debugMode = rootEl.getAttribute("react-debug-mode")?.toLowerCase() === "true";
const smarterRequestId = rootEl.getAttribute("smarter-request-id") || "";

if (!ApiUrl) throw new Error("API URL not found in root element attributes");
if (!csrfCookieName) throw new Error("CSRF token not found in root element attributes");
if (!djangoSessionCookieName) throw new Error("Django session cookie name not found in root element attributes");
if (!smarterRequestId) throw new Error("Smarter request ID not found in root element attributes");

const sessionContext: SessionContext = {
  ApiUrl,
  csrfCookieName,
  djangoSessionCookieName,
  cookieDomain,
  debugMode,
  smarterClient: projectName,
  smarterClientVersion: projectVersion,
  smarterRequestId,
  smarterCapabilities: ["terminal"],
};

console.debug(`${loggerPrefix} Session context initialized with:`, sessionContext);

// not in StrictMode, whose second mount would open, and close, a second shell.
createRoot(rootEl).render(<App sessionContext={sessionContext} />);

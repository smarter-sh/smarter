import { createRoot } from "react-dom/client";
import { loggerPrefix } from "./const";
import App from "@/App";
import type { SessionContext } from "@smarter/common";

const rootEl = document.getElementById("smarter-prompt-list-root");
if (!rootEl) throw new Error("Root element not found");

const csrfCookieName = rootEl.getAttribute("django-csrf-cookie-name");
const djangoSessionCookieName = rootEl.getAttribute("django-session-cookie-name");
const cookieDomain = rootEl.getAttribute("django-cookie-domain") || window.location.hostname;
const debugMode = rootEl.getAttribute("react-debug-mode") === "true";

const ApiUrl = rootEl.getAttribute("smarter-prompt-list-api-url");

if (!ApiUrl) throw new Error("Prompt list API URL not found in root element attributes");
if (!csrfCookieName) throw new Error("CSRF token not found in root element attributes");
if (!djangoSessionCookieName) throw new Error("Django session cookie name not found in root element attributes");
if (!cookieDomain) throw new Error("Cookie domain not found in root element attributes");

const sessionContext: SessionContext = {
  ApiUrl,
  csrfCookieName,
  djangoSessionCookieName,
  cookieDomain,
  debugMode,
};
console.debug(`${loggerPrefix} Session context initialized:`, sessionContext);
createRoot(rootEl).render(<App sessionContext={sessionContext} />);

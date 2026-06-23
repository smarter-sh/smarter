import { createRoot } from "react-dom/client";
import type { SessionContext } from "@smarter/common";

import { loggerPrefix, projectName, projectVersion } from "@/const";
import App from "./App.tsx";

const rootEl = document.getElementById("smarter-dashboard-root");
if (!rootEl) throw new Error("Root element not found");

const csrfCookieName = rootEl.getAttribute("smarter-csrf-cookie-name");
const djangoSessionCookieName = rootEl.getAttribute("smarter-django-session-cookie-name");
const cookieDomain = rootEl.getAttribute("smarter-cookie-domain") || window.location.hostname;

const myResourcesApiUrl = rootEl.getAttribute("smarter-my-resources-api-url");
const serviceHealthApiUrl = rootEl.getAttribute("smarter-service-health-api-url");
const debugMode = rootEl.getAttribute("react-debug-mode")?.toLowerCase() === "true";
const smarterRequestId = rootEl.getAttribute("smarter-request-id") || "";

const smarterClient = projectName;
const smarterClientVersion = projectVersion;
const smarterCapabilities = ["custom"];

if (!myResourcesApiUrl) throw new Error("My Resources API URL not found in root element attributes");
if (!serviceHealthApiUrl) throw new Error("Service Health API URL not found in root element attributes");
if (!csrfCookieName) throw new Error("CSRF token not found in root element attributes");
if (!djangoSessionCookieName) throw new Error("Django session cookie name not found in root element attributes");
if (!cookieDomain) throw new Error("Cookie domain not found in root element attributes");
if (!smarterRequestId) throw new Error("Smarter request ID not found in root element attributes");

const sessionContext: SessionContext = {
    ApiUrl: myResourcesApiUrl,
    csrfCookieName,
    djangoSessionCookieName,
    cookieDomain,
    debugMode,
    smarterClient,
    smarterClientVersion,
    smarterRequestId,
    smarterCapabilities,
};
export interface AppContextInterface {
  sessionContext: SessionContext;
  myResourcesApiUrl: string;
  serviceHealthApiUrl: string;
}

const appContext: AppContextInterface = {
  sessionContext,
  myResourcesApiUrl,
  serviceHealthApiUrl,
};
console.debug(loggerPrefix, "appContext initialized with values:", appContext);
createRoot(rootEl).render(<App appContext={appContext} />);

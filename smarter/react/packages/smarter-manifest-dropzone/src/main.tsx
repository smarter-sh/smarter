import { createRoot } from "react-dom/client";
import type { SessionContext } from "@smarter/common";

import { loggerPrefix, projectName, projectVersion } from "@/const";
import App from "./App.tsx";

const rootEl = document.getElementById("smarter-manifest-dropzone-root");
if (!rootEl) throw new Error("Root element not found");

const csrfCookieName = rootEl.getAttribute("smarter-csrf-cookie-name");
const djangoSessionCookieName = rootEl.getAttribute("smarter-django-session-cookie-name");
const cookieDomain = rootEl.getAttribute("smarter-cookie-domain") || window.location.hostname;

const debugMode = rootEl.getAttribute("react-debug-mode")?.toLowerCase() === "true";
const smarterRequestId = rootEl.getAttribute("smarter-request-id") || "";
const smarterApiUrl = rootEl.getAttribute("smarter-api-url");

const smarterClient = projectName;
const smarterClientVersion = projectVersion;
const smarterCapabilities = ["custom"];

if (!csrfCookieName) throw new Error("CSRF token not found in root element attributes");
if (!djangoSessionCookieName) throw new Error("Django session cookie name not found in root element attributes");
if (!cookieDomain) throw new Error("Cookie domain not found in root element attributes");
if (!smarterRequestId) throw new Error("Smarter request ID not found in root element attributes");
if (!smarterApiUrl) throw new Error("Smarter API URL not found in root element attributes");

const sessionContext: SessionContext = {
    ApiUrl: smarterApiUrl,
    csrfCookieName,
    djangoSessionCookieName,
    cookieDomain,
    debugMode,
    smarterClient,
    smarterClientVersion,
    smarterRequestId,
    smarterCapabilities,
};

console.debug(loggerPrefix, "sessionContext initialized with values:", sessionContext);
createRoot(rootEl).render(<App sessionContext={sessionContext} />);

import { createRoot } from "react-dom/client";
import { loggerPrefix, projectName, projectVersion } from "@/const";
import App from "./App.tsx";

const rootEl = document.getElementById("smarter-terminal-emulator-root");
if (!rootEl) throw new Error("Root element not found");


const apiUrl = rootEl.getAttribute("smarter-api-path");
const debugMode = rootEl.getAttribute("react-debug-mode")?.toLowerCase() === "true";
const smarterRequestId = rootEl.getAttribute("smarter-request-id") || "";

const smarterClient = projectName;
const smarterClientVersion = projectVersion;

if (!smarterRequestId) throw new Error("Smarter request ID not found in root element attributes");

// The following attributes are expected to be set on the root element
// by the Django template, however, they are currently not in use.
// --------------------
// const csrfCookieName = rootEl.getAttribute("smarter-csrf-cookie-name");
// const djangoSessionCookieName = rootEl.getAttribute("smarter-django-session-cookie-name");
// const cookieDomain = rootEl.getAttribute("smarter-cookie-domain") || window.location.hostname;

if (!apiUrl) throw new Error("API URL not found in root element attributes");
// if (!csrfCookieName) throw new Error("CSRF token not found in root element attributes");
// if (!djangoSessionCookieName) throw new Error("Django session cookie name not found in root element attributes");
// if (!cookieDomain) throw new Error("Cookie domain not found in root element attributes");

console.debug(`${loggerPrefix} Initialized with API URL: ${apiUrl}`);
console.debug(`${loggerPrefix} Debug mode: ${debugMode}`);
console.debug(`${loggerPrefix} Smarter client: ${smarterClient}`);
console.debug(`${loggerPrefix} Smarter client version: ${smarterClientVersion}`);
console.debug(`${loggerPrefix} Smarter request ID: ${smarterRequestId}`);
createRoot(rootEl).render(<App apiUrl={apiUrl} />);

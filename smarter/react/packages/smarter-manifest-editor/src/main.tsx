import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import type { SessionContext } from "@smarter/common";

import { loggerPrefix, projectName, projectVersion } from "@/const.tsx";
import App from "@/App.tsx";

const rootEl = document.getElementById("smarter-manifest-editor-root");
if (!rootEl) throw new Error("Root element not found");

const manifestDataId = rootEl.getAttribute("smarter-manifest-data-id");
const applyApiUrl = rootEl.getAttribute("smarter-apply-api-url");
const validateApiUrl = rootEl.getAttribute("smarter-validate-api-url");
const deleteApiUrl = rootEl.getAttribute("smarter-delete-api-url");
const kindPlaceholder = rootEl.getAttribute("smarter-kind-placeholder");
const csrfCookieName = rootEl.getAttribute("django-csrf-cookie-name");
const djangoSessionCookieName = rootEl.getAttribute("django-session-cookie-name");
const cookieDomain = rootEl.getAttribute("django-cookie-domain") || window.location.hostname;
const debugMode = rootEl.getAttribute("react-debug-mode")?.toLowerCase() === "true";
const smarterRequestId = rootEl.getAttribute("smarter-request-id") || "";

if (!manifestDataId) throw new Error("Manifest data id not found in root element attributes");
if (!applyApiUrl) throw new Error("Apply API URL not found in root element attributes");
if (!validateApiUrl) throw new Error("Validate API URL not found in root element attributes");
if (!deleteApiUrl) throw new Error("Delete API URL not found in root element attributes");
if (!kindPlaceholder) throw new Error("Kind placeholder not found in root element attributes");
if (!csrfCookieName) throw new Error("CSRF cookie name not found in root element attributes");
if (!djangoSessionCookieName) throw new Error("Django session cookie name not found in root element attributes");
if (!smarterRequestId) throw new Error("Smarter request ID not found in root element attributes");

// the manifest, as YAML, from Django's json_script.
const manifestEl = document.getElementById(manifestDataId);
if (!manifestEl) throw new Error(`Manifest data element ${manifestDataId} not found`);
const initialManifest = JSON.parse(manifestEl.textContent || '""') as string;

const sessionContext: SessionContext = {
  ApiUrl: applyApiUrl,
  csrfCookieName,
  djangoSessionCookieName,
  cookieDomain,
  debugMode,
  smarterClient: projectName,
  smarterClientVersion: projectVersion,
  smarterRequestId,
  smarterCapabilities: ["custom"],
};

console.debug(`${loggerPrefix} Session context initialized with:`, sessionContext);

createRoot(rootEl).render(
  <StrictMode>
    <App
      sessionContext={sessionContext}
      initialManifest={initialManifest}
      applyApiUrl={applyApiUrl}
      validateApiUrl={validateApiUrl}
      deleteApiUrl={deleteApiUrl}
      kindPlaceholder={kindPlaceholder}
    />
  </StrictMode>,
);

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import type { SessionContext } from "@smarter/common";

import { loggerPrefix, projectName, projectVersion } from "@/const.tsx";
import App from "./App.tsx";

const rootEl = document.getElementById("smarter-prompt-passthrough-root");
if (!rootEl) throw new Error("Root element not found");

const ApiUrl = rootEl.getAttribute("smarter-api-path");
const csrfCookieName = rootEl.getAttribute("smarter-csrf-cookie-name");
const djangoSessionCookieName = rootEl.getAttribute("smarter-django-session-cookie-name");
const cookieDomain = rootEl.getAttribute("smarter-cookie-domain") || window.location.hostname;
const llmProviderId = parseInt(rootEl.getAttribute("smarter-llm-provider-id") || "1", 10);
const templateId = parseInt(rootEl.getAttribute("smarter-template-id") || "1", 10);
const providerApiUrl = rootEl.getAttribute("smarter-provider-api-url") || "";
const debugMode = rootEl.getAttribute("react-debug-mode")?.toLowerCase() === "true";
const smarterRequestId = rootEl.getAttribute("smarter-request-id") || "";

const smarterClient = projectName;
const smarterClientVersion = projectVersion;
const smarterCapabilities = ["custom"];

if (!ApiUrl) throw new Error("API URL not found in root element attributes");
if (!csrfCookieName) throw new Error("CSRF token not found in root element attributes");
if (!djangoSessionCookieName) throw new Error("Django session cookie name not found in root element attributes");
if (!cookieDomain) throw new Error("Cookie domain not found in root element attributes");
if (!llmProviderId) throw new Error("LLM provider ID not found in root element attributes");
if (!templateId) throw new Error("Template ID not found in root element attributes");
if (!providerApiUrl) throw new Error("Provider API URL not found in root element attributes");
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
  smarterCapabilities,
};

console.debug(`${loggerPrefix} Session context initialized with:`, sessionContext);

createRoot(rootEl).render(
  <StrictMode>
    <App
      sessionContext={sessionContext}
      defaultLLMProviderId={llmProviderId}
      defaultTemplateId={templateId}
      providerApiUrl={providerApiUrl}
    />
  </StrictMode>,
);

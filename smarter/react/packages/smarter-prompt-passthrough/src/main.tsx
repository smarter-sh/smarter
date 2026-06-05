import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { loggerPrefix } from "@/const.tsx";
import App from "./App.tsx";

const rootEl = document.getElementById("smarter-prompt-passthrough-root");
if (!rootEl) throw new Error("Root element not found");

const apiUrl = rootEl.getAttribute("smarter-api-path");
const csrfCookieName = rootEl.getAttribute("smarter-csrf-cookie-name");
const djangoSessionCookieName = rootEl.getAttribute("smarter-django-session-cookie-name");
const cookieDomain = rootEl.getAttribute("smarter-cookie-domain") || window.location.hostname;
const llmProviderId = rootEl.getAttribute("smarter-llm-provider-id") || "1";
const templateId = rootEl.getAttribute("smarter-template-id") || "1";
const providerApiUrl = rootEl.getAttribute("smarter-provider-api-url") || "";

if (!apiUrl) throw new Error("API URL not found in root element attributes");
if (!csrfCookieName) throw new Error("CSRF token not found in root element attributes");
if (!djangoSessionCookieName) throw new Error("Django session cookie name not found in root element attributes");
if (!cookieDomain) throw new Error("Cookie domain not found in root element attributes");
if (!llmProviderId) throw new Error("LLM provider ID not found in root element attributes");
if (!templateId) throw new Error("Template ID not found in root element attributes");
if (!providerApiUrl) throw new Error("Provider API URL not found in root element attributes");

export type SessionContextType = {
  apiUrl: string;
  csrfCookieName: string;
  djangoSessionCookieName: string;
  cookieDomain: string;
  llmProviderId: string;
  templateId: string;
  providerApiUrl: string;
};

const sessionContext: SessionContextType = {
  apiUrl,
  csrfCookieName,
  djangoSessionCookieName,
  cookieDomain,
  llmProviderId,
  templateId,
  providerApiUrl,
};
console.debug(`${loggerPrefix} Session context initialized with:`, sessionContext);

createRoot(rootEl).render(
  <StrictMode>
    <App sessionContext={sessionContext} />
  </StrictMode>,
);

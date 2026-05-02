import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App.tsx";

const rootEl = document.getElementById("smarter-terminal-emulator-root");
if (!rootEl) throw new Error("Root element not found");

const apiUrl = rootEl.getAttribute("smarter-api-path");
const csrfCookieName = rootEl.getAttribute("smarter-csrf-cookie-name");
const csrftoken = rootEl.getAttribute("django-csrftoken");
const djangoSessionCookieName = rootEl.getAttribute(
  "smarter-django-session-cookie-name",
);
const cookieDomain =
  rootEl.getAttribute("smarter-cookie-domain") || window.location.hostname;

if (!apiUrl) throw new Error("API URL not found in root element attributes");
if (!csrfCookieName)
  throw new Error("CSRF token not found in root element attributes");
if (!djangoSessionCookieName)
  throw new Error(
    "Django session cookie name not found in root element attributes",
  );
if (!cookieDomain)
  throw new Error("Cookie domain not found in root element attributes");
if (!csrftoken)
  throw new Error("CSRF token value not found in root element attributes");

createRoot(rootEl).render(
  <StrictMode>
    <App
      apiUrl={apiUrl}
    />
  </StrictMode>,
);

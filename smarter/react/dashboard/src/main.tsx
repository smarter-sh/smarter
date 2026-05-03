import { createRoot } from "react-dom/client";
import App from "./App.tsx";

const rootEl = document.getElementById("smarter-dashboard-root");
if (!rootEl) throw new Error("Root element not found");

const csrfCookieName = rootEl.getAttribute("smarter-csrf-cookie-name");
const csrftoken = rootEl.getAttribute("django-csrftoken");
const djangoSessionCookieName = rootEl.getAttribute(
  "smarter-django-session-cookie-name",
);
const cookieDomain =
  rootEl.getAttribute("smarter-cookie-domain") || window.location.hostname;

const myResourcesApiUrl = rootEl.getAttribute("smarter-my-resources-api-url");
const serviceHealthApiUrl = rootEl.getAttribute("smarter-service-health-api-url");

if (!myResourcesApiUrl) throw new Error("My Resources API URL not found in root element attributes");
if (!serviceHealthApiUrl) throw new Error("Service Health API URL not found in root element attributes");
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
  <App
    myResourcesApiUrl={myResourcesApiUrl}
    serviceHealthApiUrl={serviceHealthApiUrl}
    csrfCookieName={csrfCookieName}
    csrftoken={csrftoken}
    djangoSessionCookieName={djangoSessionCookieName}
    cookieDomain={cookieDomain}
  />,
);

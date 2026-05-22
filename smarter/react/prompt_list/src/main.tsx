import { createRoot } from "react-dom/client";
import App from "@/App";
import type { SessionContext } from "@/lib/Types";

const rootEl = document.getElementById("smarter-prompt-list-root");
if (!rootEl) throw new Error("Root element not found");

const csrfCookieName = rootEl.getAttribute("django-csrf-cookie-name");
const csrftoken = rootEl.getAttribute("django-csrf-token");
const djangoSessionCookieName = rootEl.getAttribute(
  "django-session-cookie-name",
);
const cookieDomain =
  rootEl.getAttribute("django-cookie-domain") || window.location.hostname;

const promptListApiUrl = rootEl.getAttribute("smarter-prompt-list-api-url");

if (!promptListApiUrl)
  throw new Error("Prompt list API URL not found in root element attributes");
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

const sessionContext: SessionContext = {
  promptListApiUrl,
  csrfCookieName,
  csrftoken,
  djangoSessionCookieName,
  cookieDomain,
};

createRoot(rootEl).render(<App sessionContext={sessionContext} />);

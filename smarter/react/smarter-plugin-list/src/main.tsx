import { createRoot } from "react-dom/client";
import { loggerPrefix } from "./const";
import App from "@/App";

// new entry point based on the smarter-common TabbedListView component
// which provides a generalized interface for rendering lists of
// owned/shared objects (e.g. chatbots, plugins, etc.) with built-in
// support for loading states, error handling, and caching.
import type { Plugin } from "@/lib/Types";
import ListView from "@/components/ListView"
import CardView from "@/components/CardView"

import type { SessionContext } from "@/lib/Types";

const rootEl = document.getElementById("smarter-plugin-list-root");
if (!rootEl) throw new Error("Root element not found");

const csrfCookieName = rootEl.getAttribute("django-csrf-cookie-name");
const djangoSessionCookieName = rootEl.getAttribute("django-session-cookie-name");
const cookieDomain = rootEl.getAttribute("django-cookie-domain") || window.location.hostname;

const ApiUrl = rootEl.getAttribute("smarter-plugin-list-api-url");

if (!ApiUrl) throw new Error("Plugin list API URL not found in root element attributes");
if (!csrfCookieName) throw new Error("CSRF token not found in root element attributes");
if (!djangoSessionCookieName) throw new Error("Django session cookie name not found in root element attributes");
if (!cookieDomain) throw new Error("Cookie domain not found in root element attributes");

const sessionContext: SessionContext = {
  ApiUrl,
  csrfCookieName,
  djangoSessionCookieName,
  cookieDomain,
  objectType: {} as Plugin,
  objectTypeName: "plugin",
  ListView: ListView,
  CardView: CardView,
};
console.debug(`${loggerPrefix} Session context initialized:`, sessionContext);
createRoot(rootEl).render(<App sessionContext={sessionContext} />);

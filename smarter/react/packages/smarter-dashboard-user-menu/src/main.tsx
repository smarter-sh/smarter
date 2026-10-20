/**
 * Main entry point for the Smarter user menu React application.
 * This module joins the DOM to the React component tree and provides
 * the necessary session context for API interactions.
 *
 * Steps:
 * 1. Retrieves necessary configuration from the root DOM element's attributes.
 * 2. Initializes a Django SessionContext.
 * 3. Renders the React App component into the root element.
 *
 * See templates/react/dashboard-user-menu.html, which the console's navbar includes on every page.
 */
import { createRoot } from "react-dom/client";
import type { SessionContext } from "@smarter/common";

import { loggerPrefix, projectName, projectVersion } from "@/lib/const";
import type { AppContext, Language } from "@/lib/Types";
import App from "@/App";

const rootEl = document.getElementById("smarter-dashboard-user-menu-root");
if (!rootEl) throw new Error("Root element not found");

const attribute = (name: string) => rootEl.getAttribute(name) || "";
const flag = (name: string) => rootEl.getAttribute(name)?.toLowerCase() === "true";

/** An attribute that the template must render, which is a bug in the template when it is missing. */
function required(name: string): string {
  const value = rootEl!.getAttribute(name);
  if (!value) throw new Error(`${name} not found in root element attributes`);
  return value;
}

const csrfCookieName = required("smarter-csrf-cookie-name");
const djangoSessionCookieName = required("smarter-django-session-cookie-name");
const cookieDomain = attribute("smarter-cookie-domain") || window.location.hostname;
const smarterRequestId = required("smarter-request-id");
const profileImageApiUrl = required("smarter-profile-image-api-url");

const sessionContext: SessionContext = {
  ApiUrl: profileImageApiUrl,
  csrfCookieName,
  djangoSessionCookieName,
  cookieDomain,
  debugMode: flag("react-debug-mode"),
  smarterClient: projectName,
  smarterClientVersion: projectVersion,
  smarterRequestId,
};

let languages: Language[] = [];
try {
  languages = JSON.parse(attribute("smarter-languages") || "[]") as Language[];
} catch (err) {
  console.error(loggerPrefix, "Invalid smarter-languages attribute", err);
}

const appContext: AppContext = {
  sessionContext,
  isAuthenticated: flag("smarter-is-authenticated"),
  user: {
    username: attribute("smarter-username"),
    email: attribute("smarter-email"),
    firstName: attribute("smarter-first-name"),
    lastName: attribute("smarter-last-name"),
    isSuperuser: flag("smarter-is-superuser"),
    isStaff: flag("smarter-is-staff"),
  },
  profileImageUrl: required("smarter-profile-image-url"),
  userProfileCount: Number.parseInt(attribute("smarter-user-profile-count"), 10) || 0,
  accountNumber: attribute("smarter-account-number"),
  accountName: attribute("smarter-account-name"),
  languages,
  currentLanguage: attribute("smarter-current-language") || "en",
  urls: {
    setLanguage: required("smarter-set-language-url"),
    next: attribute("smarter-next-url") || window.location.pathname,
    profileImageApi: profileImageApiUrl,
    userProfilesApi: required("smarter-user-profiles-api-url"),
    userProfileSelectApi: required("smarter-user-profile-select-api-url"),
    login: required("smarter-login-url"),
    logout: required("smarter-logout-url"),
  },
};
console.debug(`${loggerPrefix} App context initialized:`, appContext);
createRoot(rootEl).render(<App appContext={appContext} />);

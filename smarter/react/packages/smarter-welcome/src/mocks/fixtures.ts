/**
 * Example data for this package's development page, stories and tests: what the Django welcome api
 * returns, and the dialog's context, as the console builds it from its session. See
 * smarter.apps.dashboard.views.views.api.welcome.
 */
import type { SessionContext } from "@smarter/common";

import type { AppContext, WelcomeApiResponse } from "../lib/Types";

export const sessionContext: SessionContext = {
  ApiUrl: "/api/web/dashboard/welcome/",
  csrfCookieName: "csrftoken",
  djangoSessionCookieName: "sessionid",
  cookieDomain: "localhost",
  debugMode: false,
  smarterClient: "@smarter/welcome",
  smarterClientVersion: "0.0.0",
  smarterRequestId: "storybook-request-id",
};

/** The Django dev server's static files, which Storybook's stylesheets also come from. */
const STATIC_URL = "http://localhost:9357/static/";

export const appContext: AppContext = {
  sessionContext,
  apiUrl: "/api/web/dashboard/welcome/",
  dismissApiUrl: "/api/web/dashboard/welcome/dismiss/",
  show: true,
  showAtStartup: true,
  firstName: "Ada",
  logoUrl: `${STATIC_URL}images/logo/smarter-crop.png`,
  illustrationsUrl: `${STATIC_URL}assets/media/illustrations/dozzy-1/`,
};

export const welcome: WelcomeApiResponse = {
  welcomed: false,
  urls: {
    weather: "/workbench/llm-clients/3f2a9c/prompt/",
    llmclients: "/workbench/",
    docs: "https://docs.smarter.sh/",
    project: "https://smarter.sh/",
  },
};

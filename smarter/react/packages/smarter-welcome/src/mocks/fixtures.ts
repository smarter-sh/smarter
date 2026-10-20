/**
 * Example data for this package's stories and tests: what the Django welcome api returns, and the
 * root element's attributes. See smarter.apps.dashboard.views.views.api.welcome and
 * templates/react/welcome.html.
 */
import type { SessionContext } from "@smarter/common";

import type { AppContext, WelcomeApiResponse } from "@/lib/Types";

export const sessionContext: SessionContext = {
  ApiUrl: "/dashboard/api/welcome/",
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
  apiUrl: "/dashboard/api/welcome/",
  dismissApiUrl: "/dashboard/api/welcome/dismiss/",
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

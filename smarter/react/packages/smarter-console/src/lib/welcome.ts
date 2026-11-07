/**
 * The welcome dialog's context, and the onboarding hints' state, from the console's session. The console passes them
 * as props to @smarter/welcome and to the packages that show hints. See smarter.apps.dashboard.views.views.api.welcome
 * and onboarding.
 */
import { OnboardingHints, type OnboardingContext, type OnboardingHint } from "@smarter/onboarding";
import type { WelcomeContext } from "@smarter/welcome";

import type { ConsoleSession } from "@/contract.gen";
import { DASHBOARD_API } from "@/lib/dashboard";
import { djangoSessionContext } from "@/lib/djangoSession";

export const welcomeUrls = {
  welcome: `${DASHBOARD_API}/welcome/`,
  dismiss: `${DASHBOARD_API}/welcome/dismiss/`,
  onboardingSeen: `${DASHBOARD_API}/onboarding/seen/`,
};

/** The folder of the Keen dozzy-1 illustrations that the welcome dialog shows, which the backend serves. */
export const ILLUSTRATIONS_URL = "/static/assets/media/illustrations/dozzy-1/";

const HINTS = new Set<string>(Object.values(OnboardingHints));

/**
 * The onboarding hints' state, for a signed-in session.
 *
 * @param session - The console's session.
 * @returns The state, or null without one: no hint then shows by itself.
 */
export function onboardingContext(session: ConsoleSession): OnboardingContext | null {
  if (!session.onboarding) return null;
  const seen: OnboardingHint[] = [];
  for (const hint of session.onboarding.seen) {
    if (HINTS.has(hint)) seen.push(hint as OnboardingHint);
  }
  return {
    enabled: session.onboarding.enabled,
    apiUrl: welcomeUrls.onboardingSeen,
    seen,
    csrfCookieName: session.cookies.csrfCookieName,
    cookieDomain: session.cookies.cookieDomain || window.location.hostname,
  };
}

/**
 * The welcome dialog's context, for a signed-in session.
 *
 * @param session - The console's session.
 * @returns The context, or null for a session without the welcome dialog's state.
 */
export function welcomeContext(session: ConsoleSession): WelcomeContext | null {
  if (!session.welcome) return null;
  return {
    sessionContext: djangoSessionContext(session, welcomeUrls.welcome),
    apiUrl: welcomeUrls.welcome,
    dismissApiUrl: welcomeUrls.dismiss,
    show: session.welcome.show,
    showAtStartup: session.welcome.showAtStartup,
    firstName: session.user?.firstName ?? "",
    logoUrl: session.branding.logoUrl,
    illustrationsUrl: ILLUSTRATIONS_URL,
    onboarding: onboardingContext(session),
  };
}

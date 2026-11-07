/** An onboarding state for tests and stories, as the console builds it from its session. */
import type { OnboardingContext } from "../lib/context";

export const onboardingContext: OnboardingContext = {
  enabled: true,
  apiUrl: "/api/web/dashboard/onboarding/seen/",
  seen: [],
  csrfCookieName: "csrftoken",
  cookieDomain: "localhost",
};

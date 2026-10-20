/** An onboarding state for tests and stories, as templates/react/onboarding.html writes it. */
import type { OnboardingContext } from "../lib/context";

export const onboardingContext: OnboardingContext = {
  enabled: true,
  apiUrl: "/dashboard/api/onboarding/seen/",
  seen: [],
  csrfCookieName: "csrftoken",
  cookieDomain: "localhost",
};

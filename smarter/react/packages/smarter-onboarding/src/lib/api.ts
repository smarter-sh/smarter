/**
 * The onboarding seen api, smarter.apps.dashboard.views.views.api.onboarding.OnboardingSeenView.
 */
import { getCookie } from "@smarter/common";

import type { OnboardingHint, OnboardingOutcome } from "./const";
import type { OnboardingContext } from "./context";

/**
 * Records what the user did with a hint, so that it no longer shows by itself.
 *
 * The request is sent with keepalive, so that it completes when the user has clicked a link that a hint
 * points to, and the browser is already leaving the page.
 *
 * :param context: The page's onboarding state.
 * :param hint: The hint.
 * :param outcome: What the user did with it.
 * :returns: The response.
 * :raises Error: When the api answers with an error.
 */
export async function recordOnboarding(
  context: OnboardingContext,
  hint: OnboardingHint,
  outcome: OnboardingOutcome,
): Promise<Response> {
  const csrfToken = getCookie({ name: context.csrfCookieName, domain: context.cookieDomain }) ?? "";
  const response = await fetch(context.apiUrl, {
    method: "POST",
    credentials: "include",
    keepalive: true,
    headers: { Accept: "application/json", "Content-Type": "application/json", "X-CSRFToken": csrfToken },
    body: JSON.stringify({ hint, outcome }),
  });
  if (!response.ok) throw new Error(`Request failed: ${response.status}`);
  return response;
}

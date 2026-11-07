/**
 * The onboarding state: the session's onboarding (ConsoleOnboarding, smarter.apps.api.web.session). The console
 * builds it from its session and passes it as a prop to the packages that show hints. readOnboardingContext() is their
 * fallback without one: it reads the state from a JSON script element, if a page writes one, which none of the
 * console's pages do.
 */
import { ONBOARDING_CONTEXT_ID, OnboardingHints, type OnboardingHint } from "./const";

export interface OnboardingContext {
  /** Whether hints show by themselves: the enable_web_console_onboarding_hints waffle switch. */
  enabled: boolean;
  /** The onboarding seen api, which records what the user did with a hint. */
  apiUrl: string;
  /** The hints that the user has seen. */
  seen: OnboardingHint[];
  csrfCookieName: string;
  cookieDomain: string;
}

const HINTS = new Set<string>(Object.values(OnboardingHints));

/**
 * Reads the page's onboarding state.
 *
 * :param doc: The document, by default the page's.
 * :returns: The state, or null when the page has none, e.g. a page without a signed-in user, or when it
 *   isn't valid, in which case no hint shows.
 */
export function readOnboardingContext(doc: Document = document): OnboardingContext | null {
  const text = doc.getElementById(ONBOARDING_CONTEXT_ID)?.textContent;
  if (!text) return null;
  try {
    const data = JSON.parse(text) as Partial<OnboardingContext>;
    if (
      typeof data.enabled !== "boolean" ||
      typeof data.apiUrl !== "string" ||
      !Array.isArray(data.seen) ||
      typeof data.csrfCookieName !== "string" ||
      typeof data.cookieDomain !== "string"
    ) {
      return null;
    }
    return { ...(data as OnboardingContext), seen: data.seen.filter((hint) => HINTS.has(hint)) };
  } catch {
    return null;
  }
}

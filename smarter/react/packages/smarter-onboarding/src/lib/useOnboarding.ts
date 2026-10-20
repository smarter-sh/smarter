/**
 * The onboarding state of a React app: which hints show by themselves, and how to record that the user has
 * seen one.
 */
import { useCallback, useState } from "react";

import { recordOnboarding } from "./api";
import type { OnboardingHint, OnboardingOutcome } from "./const";
import { readOnboardingContext, type OnboardingContext } from "./context";

export interface Onboarding {
  /** Whether hints show by themselves on this page. */
  enabled: boolean;
  /** Whether the hint shows by itself: hints are enabled, and the user hasn't seen it. */
  shouldShow: (hint: OnboardingHint) => boolean;
  /**
   * Records what the user did with the hint, which then no longer shows by itself. A hint that the user has
   * already seen, e.g. a tour taken again, isn't recorded again. A failed request is logged, and the hint
   * shows again on the next page.
   */
  record: (hint: OnboardingHint, outcome: OnboardingOutcome) => void;
}

/**
 * :param context: The page's onboarding state. By default, the one that the page holds, from
 *   readOnboardingContext(). Tests and stories pass their own, or null for a page without one.
 */
export function useOnboarding(context?: OnboardingContext | null): Onboarding {
  const [state] = useState(() => (context === undefined ? readOnboardingContext() : context));
  const [seen, setSeen] = useState<ReadonlySet<OnboardingHint>>(() => new Set(state?.seen ?? []));
  const enabled = !!state?.enabled;

  const shouldShow = useCallback((hint: OnboardingHint) => enabled && !seen.has(hint), [enabled, seen]);

  const record = useCallback(
    (hint: OnboardingHint, outcome: OnboardingOutcome) => {
      if (!state || seen.has(hint)) return;
      setSeen((previous) => new Set(previous).add(hint));
      recordOnboarding(state, hint, outcome).catch((error: Error) => {
        console.error("[@smarter/onboarding] Failed to record the hint", hint, error);
      });
    },
    [state, seen],
  );

  return { enabled, shouldShow, record };
}

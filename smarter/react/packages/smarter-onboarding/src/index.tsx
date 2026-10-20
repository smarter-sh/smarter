/**
 * @smarter/onboarding: the web console's onboarding hints, which point a new user to where to go next.
 *
 * - Spotlight: a sparkling ring around one element, and a short note beside it.
 * - Tour: a guided tour of a page, step by step.
 * - useOnboarding(): which hints show by themselves, from the page's onboarding state, and how to record
 *   that the user has seen one, with the onboarding seen api.
 */
export { default as Spotlight } from "./components/Spotlight/Component";
export type { SpotlightOutcome, SpotlightProps } from "./components/Spotlight/Component";
export { default as Tour } from "./components/Tour/Component";
export type { TourOutcome, TourProps, TourStep } from "./components/Tour/Component";
export { recordOnboarding } from "./lib/api";
export { ONBOARDING_CONTEXT_ID, ONBOARDING_TARGET_ATTRIBUTE, OnboardingHints, OnboardingOutcomes } from "./lib/const";
export type { OnboardingHint, OnboardingOutcome } from "./lib/const";
export { readOnboardingContext } from "./lib/context";
export type { OnboardingContext } from "./lib/context";
export { findTarget, isVisible, onboardingSelector, waitForTarget, waitUntil } from "./lib/targets";
export { useOnboarding } from "./lib/useOnboarding";
export type { Onboarding } from "./lib/useOnboarding";

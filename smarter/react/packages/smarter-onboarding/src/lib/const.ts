/**
 * The onboarding hints, and what a user can do with one. Each id is also a choice of the Django model's
 * fields, OnboardingHints and OnboardingOutcomes in smarter/apps/dashboard/models.py, whose test checks
 * that they match.
 */
export const OnboardingHints = {
  SIDEBAR_LLMCLIENTS: "sidebar_llmclients",
  LLMCLIENT_WEATHER: "llmclient_weather",
  WORKBENCH_TOUR: "workbench_tour",
} as const;

export type OnboardingHint = (typeof OnboardingHints)[keyof typeof OnboardingHints];

export const OnboardingOutcomes = {
  CLICKED: "clicked",
  DISMISSED: "dismissed",
  COMPLETED: "completed",
  VISITED: "visited",
} as const;

export type OnboardingOutcome = (typeof OnboardingOutcomes)[keyof typeof OnboardingOutcomes];

/**
 * The attribute that marks an element that a hint points to, e.g. data-smarter-onboarding="sidebar-llmclients"
 * on the console sidebar's LLM Clients link (src/lib/sidebar.ts in @smarter/console).
 */
export const ONBOARDING_TARGET_ATTRIBUTE = "data-smarter-onboarding";

/**
 * The id of the JSON script element that readOnboardingContext() reads, if a page writes one. None of the console's
 * pages do: the console passes its session's onboarding state as a prop.
 */
export const ONBOARDING_CONTEXT_ID = "smarter-onboarding";

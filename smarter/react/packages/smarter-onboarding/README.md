# Smarter Onboarding

The web console's onboarding hints, which point a new user to where to go next: a sparkling spotlight on
the sidebar's LLM Clients link, then on the Get Weather LLMClient, then a guided tour of the Prompt
Engineer's Workbench. A library, built into `dist/` like `@smarter/common`:

- `Spotlight`: a sparkling ring around one element, and a short note beside it.
- `Tour`: a guided tour, step by step, that dims the page around each part.
- `useOnboarding()`: which hints show by themselves, from the page's onboarding state, and `record()`.
- `waitForTarget()`, `waitUntil()`, `findTarget()`, `onboardingSelector()`.

Its consumers: [@smarter/welcome](../smarter-welcome) (the sidebar hint),
[@smarter/llmclient-list](../smarter-llmclient-list) (the Get Weather hint) and
[@smarter/workbench](../smarter-workbench) (the tour). See also:

- `@smarter/console`, which builds the onboarding state from its session (`src/lib/welcome.ts` there) and
  passes it as a prop to the packages that show hints. Without that prop, `useOnboarding()` falls back to
  `readOnboardingContext()`, which reads the state from a JSON script element if a page writes one; none
  of the console's pages do.
- [smarter.apps.dashboard.views.views.api.onboarding](../../../smarter/apps/dashboard/views/views/api/onboarding.py),
  the api that records what a user did with a hint, in the `OnboardingHint` model
- the `enable_web_console_onboarding_hints` waffle switch

## Setup

```console
npm run build                                     # the library, for its consumers
make react-storybook APP=smarter-onboarding       # Storybook
```

/**
 * The first onboarding hint: a sparkling spotlight on the sidebar's LLM Clients link, with a short note, so
 * that a new user's first click takes them to their LLMClients. The welcome app shows it while the welcome
 * dialog is closed, until the user clicks the link or Got it.
 *
 * A user who is already among their LLMClients, e.g. on the list or in the workbench, has got there, and the
 * hint is recorded as "visited" without showing. While the link is off screen, e.g. in the sidebar's drawer
 * on a phone, the hint waits.
 *
 * :param onboarding: The app's onboarding state, from useOnboarding().
 */
import { useEffect, useState } from "react";
import { gettext } from "@smarter/common";
import {
  OnboardingHints,
  OnboardingOutcomes,
  Spotlight,
  onboardingSelector,
  waitForTarget,
  type Onboarding,
} from "@smarter/onboarding";

/** The sidebar's LLM Clients link, in templates/dashboard/sidebar.html. */
const SIDEBAR_LLMCLIENTS_SELECTOR = onboardingSelector("sidebar-llmclients");

const HINT = OnboardingHints.SIDEBAR_LLMCLIENTS;

/** Whether the page is the link's page, or one below it, e.g. /workbench/ and /workbench/llm-clients/... */
function isUnder(link: HTMLAnchorElement): boolean {
  const path = new URL(link.href, window.location.href).pathname;
  return path !== "/" && window.location.pathname.startsWith(path);
}

function SidebarHint({ onboarding }: { onboarding: Onboarding }) {
  const { shouldShow, record } = onboarding;
  const show = shouldShow(HINT);
  const [target, setTarget] = useState<HTMLElement | null>(null);

  useEffect(() => {
    if (!show) return;
    const link = document.querySelector<HTMLAnchorElement>(SIDEBAR_LLMCLIENTS_SELECTOR);
    if (!link) return;
    if (isUnder(link)) {
      record(HINT, OnboardingOutcomes.VISITED);
      return;
    }
    const controller = new AbortController();
    waitForTarget(SIDEBAR_LLMCLIENTS_SELECTOR, { signal: controller.signal, timeout: 60000 }).then((element) => {
      if (element) setTarget(element);
    });
    return () => controller.abort();
  }, [show, record]);

  if (!show || !target) return null;
  return (
    <Spotlight
      target={target}
      icon="ki-rocket"
      text={gettext("Start building your AI masterpiece here.")}
      onDone={(outcome) => record(HINT, outcome)}
    />
  );
}

export default SidebarHint;

/**
 * The second onboarding hint: a sparkling spotlight on the Get Weather LLMClient's name in the list, with a
 * short note, so that a new user starts with the example that the welcome tour suggests. Its name opens the
 * LLMClient's detail (see TabbedListView), whose Chat button opens its chat in the Prompt Engineer's
 * Workbench, where the workbench's guided tour takes over. It shows until the user clicks the name or Got it.
 *
 * The list loads after the page, so the hint waits for the name to appear. A user who doesn't have a Get
 * Weather LLMClient, or doesn't open the tab that lists it, doesn't see the hint.
 *
 * :param onboarding: The app's onboarding state, from useOnboarding().
 */
import { useEffect, useState } from "react";
import { gettext } from "@smarter/common";
import { OnboardingHints, Spotlight, onboardingSelector, waitForTarget, type Onboarding } from "@smarter/onboarding";

import { WEATHER_TARGET } from "@/components/WeatherHint/const";

const HINT = OnboardingHints.LLMCLIENT_WEATHER;

function WeatherHint({ onboarding }: { onboarding: Onboarding }) {
  const { shouldShow, record } = onboarding;
  const show = shouldShow(HINT);
  const [target, setTarget] = useState<HTMLElement | null>(null);

  useEffect(() => {
    if (!show) return;
    const controller = new AbortController();
    waitForTarget(onboardingSelector(WEATHER_TARGET), { signal: controller.signal, timeout: 60000 }).then((element) => {
      if (element) setTarget(element);
    });
    return () => controller.abort();
  }, [show]);

  if (!show || !target || !target.isConnected) return null;
  return (
    <Spotlight
      target={target}
      icon="ki-cloud"
      title={gettext("Start with the weather LLMClient")}
      text={gettext(
        "Click its name to see how it's built, then its Chat button to chat with it in the Prompt Engineer's Workbench. Ask it about the weather anywhere in the world, and see how an LLM uses a tool to answer.",
      )}
      onDone={(outcome) => record(HINT, outcome)}
    />
  );
}

export default WeatherHint;

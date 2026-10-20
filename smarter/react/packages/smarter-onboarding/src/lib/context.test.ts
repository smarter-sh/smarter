import { afterEach, describe, expect, it } from "vitest";

import { readOnboardingContext } from "@/lib/context";
import { onboardingContext } from "@/mocks/context";

function writeContext(text: string) {
  const script = document.createElement("script");
  script.type = "application/json";
  script.id = "smarter-onboarding";
  script.textContent = text;
  document.body.append(script);
}

describe("readOnboardingContext", () => {
  afterEach(() => document.getElementById("smarter-onboarding")?.remove());

  it("reads the page's onboarding state", () => {
    writeContext(JSON.stringify({ ...onboardingContext, seen: ["sidebar_llmclients"] }));
    expect(readOnboardingContext()).toEqual({ ...onboardingContext, seen: ["sidebar_llmclients"] });
  });

  it("leaves out hints that it doesn't know", () => {
    writeContext(JSON.stringify({ ...onboardingContext, seen: ["workbench_tour", "a_future_hint"] }));
    expect(readOnboardingContext()?.seen).toEqual(["workbench_tour"]);
  });

  it("is null for a page without one, or with one that isn't valid", () => {
    expect(readOnboardingContext()).toBeNull();
    writeContext("not json");
    expect(readOnboardingContext()).toBeNull();
    document.getElementById("smarter-onboarding")?.remove();
    writeContext(JSON.stringify({ ...onboardingContext, enabled: "yes" }));
    expect(readOnboardingContext()).toBeNull();
  });
});

import { afterEach, describe, expect, it, vi } from "vitest";

import { findTarget, isVisible, onboardingSelector, waitForTarget, waitUntil } from "@/lib/targets";
import { addTarget, removeTargets, stubBox } from "@/mocks/targets";

describe("targets", () => {
  afterEach(() => {
    removeTargets();
    vi.useRealTimers();
  });

  it("selects the element that a hint names", () => {
    expect(onboardingSelector("sidebar-llmclients")).toBe('[data-smarter-onboarding="sidebar-llmclients"]');
  });

  it("finds an element on screen, and not one without a size, or hidden, inert or aria-hidden", () => {
    const shown = addTarget('<a data-smarter-onboarding="link" href="/">Link</a>');
    expect(isVisible(shown)).toBe(true);
    expect(findTarget(onboardingSelector("link"))).toBe(shown);

    const sizeless = addTarget("<a>Sizeless</a>", { top: 0, left: 0, width: 0, height: 0 });
    expect(isVisible(sizeless)).toBe(false);

    for (const attribute of ["hidden", "inert", 'aria-hidden="true"']) {
      const parent = addTarget(`<div ${attribute}><button>Tab</button></div>`);
      const button = parent.querySelector("button") as HTMLElement;
      stubBox(button, { top: 0, left: 0, width: 40, height: 20 });
      expect(isVisible(button)).toBe(false);
    }

    const invisible = addTarget('<span style="visibility: hidden">Hidden</span>');
    expect(isVisible(invisible)).toBe(false);
    expect(findTarget(".missing")).toBeNull();
  });

  it("waits for an element to come on screen", async () => {
    vi.useFakeTimers();
    const waiting = waitForTarget(onboardingSelector("later"));
    await vi.advanceTimersByTimeAsync(500);
    const element = addTarget('<a data-smarter-onboarding="later" href="/">Later</a>');
    await vi.advanceTimersByTimeAsync(250);
    await expect(waiting).resolves.toBe(element);
  });

  it("waits until a check passes, for as long as the page is open by default", async () => {
    vi.useFakeTimers();
    let open = true;
    const closed = waitUntil(() => !open);
    await vi.advanceTimersByTimeAsync(60000);
    open = false;
    await vi.advanceTimersByTimeAsync(250);
    await expect(closed).resolves.toBe(true);
  });

  it("resolves at once for an element already on screen", async () => {
    const element = addTarget('<a data-smarter-onboarding="now" href="/">Now</a>');
    await expect(waitForTarget(onboardingSelector("now"))).resolves.toBe(element);
  });

  it("gives up after the timeout, or when aborted", async () => {
    vi.useFakeTimers();
    const timedOut = waitForTarget(".never", { timeout: 1000 });
    await vi.advanceTimersByTimeAsync(1250);
    await expect(timedOut).resolves.toBeNull();

    const controller = new AbortController();
    const aborted = waitForTarget(".never", { signal: controller.signal });
    controller.abort();
    await expect(aborted).resolves.toBeNull();
    await expect(waitForTarget(".never", { signal: controller.signal })).resolves.toBeNull();
  });
});

import { describe, expect, it } from "vitest";

import { workbenchTourSteps } from "@/components/WorkbenchTour/steps";

describe("workbenchTourSteps", () => {
  it("starts with an introduction, and points each other step to a part of the workbench", () => {
    const steps = workbenchTourSteps();
    expect(steps[0].target).toBeUndefined();
    for (const step of steps.slice(1)) {
      expect(step.target).toBeTruthy();
      expect(() => document.querySelector(step.target as string)).not.toThrow();
    }
    expect(new Set(steps.map((step) => step.title)).size).toBe(steps.length);
    for (const step of steps) expect(step.icon).toMatch(/^ki-[a-z0-9-]+$/);
  });

  it("points to each of the Console's tabs, within the Console, and selects it", () => {
    const steps = workbenchTourSteps();
    const targets = steps.map((step) => step.target);
    // only the tabs: a click on the mode switch, the Console's button or the Help menu would change the page.
    expect(steps.filter((step) => step.activate).map((step) => step.target)).toEqual(
      targets.filter((target) => target?.startsWith("#chatapp_console")),
    );
    for (const tab of [
      "manifest",
      "architecture",
      "server_logs",
      "chat_tool_call_history",
      "chat_config",
      "deployment",
    ]) {
      expect(targets).toContain(`#chatapp_console [id="${tab}"]`);
    }
  });
});

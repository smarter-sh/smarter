import { describe, expect, it } from "vitest";
import { didYouKnowFacts } from "@smarter/didyouknow";

import { pickDidYouKnow } from "@/components/WelcomeDialog/didYouKnow";

describe("pickDidYouKnow", () => {
  it("picks a step and a fact from the random numbers, within range", () => {
    const facts = didYouKnowFacts();
    expect(pickDidYouKnow(8, () => 0)).toEqual({ step: 0, fact: facts[0] });
    expect(pickDidYouKnow(8, () => 0.999)).toEqual({ step: 7, fact: facts[facts.length - 1] });
  });

  it("uses Math.random by default", () => {
    const { step, fact } = pickDidYouKnow(8);
    expect(step).toBeGreaterThanOrEqual(0);
    expect(step).toBeLessThan(8);
    expect(didYouKnowFacts()).toContainEqual(fact);
  });
});

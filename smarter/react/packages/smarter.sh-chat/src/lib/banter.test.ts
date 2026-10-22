import { describe, expect, it } from "vitest";

import { BANTER_DELAY_MS, BANTER_INTERVAL_MS, BANTER_VERBS, idleBanter } from "@/lib/banter";
import { activateLanguage } from "@/lib/i18n";

describe("idleBanter", () => {
  it("is a sentence with one of the silly verbs", () => {
    activateLanguage("en");
    expect(idleBanter(() => 0)).toBe("Hang on while I flabberjabber your answer…");
    const line = idleBanter();
    expect(BANTER_VERBS.some((verb) => line.includes(verb))).toBe(true);
    expect(line).not.toContain("%(verb)s");
  });

  it("picks the last sentence and verb for a random number just under 1", () => {
    activateLanguage("en");
    expect(idleBanter(() => 0.999999)).toBe(`Still here! Just pausing to ${BANTER_VERBS.at(-1)}…`);
  });

  it("translates the sentence, but not the verb", () => {
    activateLanguage("es");
    const line = idleBanter(() => 0);
    expect(line).toContain("flabberjabber");
    expect(line).not.toBe("Hang on while I flabberjabber your answer…");
    activateLanguage("en");
  });

  it("starts after three seconds, and changes every ten", () => {
    expect(BANTER_DELAY_MS).toBe(3_000);
    expect(BANTER_INTERVAL_MS).toBe(10_000);
  });
});

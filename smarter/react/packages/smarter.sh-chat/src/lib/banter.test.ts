import { describe, expect, it } from "vitest";

import {
  BANTER_ADJECTIVE_ODDS,
  BANTER_ADJECTIVES,
  BANTER_DELAY_MS,
  BANTER_INTERVAL_MS,
  BANTER_NOUNS,
  BANTER_VERBS,
  idleBanter,
} from "@/lib/banter";
import { activateLanguage } from "@/lib/i18n";

describe("idleBanter", () => {
  it("is a sentence with one of the silly verbs and one of the silly nouns", () => {
    activateLanguage("en");
    expect(idleBanter(() => 0)).toBe("Hang on while I flabberjabber the doohickey…");
    const line = idleBanter();
    expect(BANTER_VERBS.some((verb) => line.includes(verb))).toBe(true);
    expect(BANTER_NOUNS.some((noun) => line.includes(noun))).toBe(true);
    expect(line).not.toMatch(/%\((verb|noun)\)s/);
  });

  it("picks the last sentence, verb, noun and adjective for a random number just under 1", () => {
    activateLanguage("en");
    expect(idleBanter(() => 0.999999)).toBe(
      `Still here! Just pausing to ${BANTER_VERBS.at(-1)} the ${BANTER_ADJECTIVES.at(-1)} ${BANTER_NOUNS.at(-1)}…`,
    );
  });

  it("puts an adjective before the noun in about a third of the lines", () => {
    activateLanguage("en");
    expect(BANTER_ADJECTIVE_ODDS).toBeCloseTo(1 / 3);
    // the random numbers of the sentence, the verb, the noun, whether there's an adjective, and which.
    const banter = (adjectiveChance: number) => {
      const numbers = [0, 0, 0, adjectiveChance, 0];
      return idleBanter(() => numbers.shift() ?? 0);
    };
    expect(banter(0.6)).toBe("Hang on while I flabberjabber the doohickey…");
    expect(banter(0.7)).toBe(`Hang on while I flabberjabber the ${BANTER_ADJECTIVES[0]} doohickey…`);
  });

  it("translates the sentence, but not the verb or the noun", () => {
    for (const language of ["es", "fr", "pt-BR"]) {
      activateLanguage(language);
      const line = idleBanter(() => 0);
      expect(line).toContain("flabberjabber");
      expect(line).toContain("doohickey");
      expect(line).not.toBe("Hang on while I flabberjabber the doohickey…");
      expect(line).not.toMatch(/%\((verb|noun)\)s/);
    }
    activateLanguage("en");
  });

  it("has nouns and adjectives that every translation's articles fit: a consonant other than h first, no repeats", () => {
    expect(BANTER_NOUNS.filter((noun) => /^[aeiouh]/i.test(noun))).toEqual([]);
    expect(BANTER_ADJECTIVES.filter((adjective) => /^[aeiouh]/i.test(adjective))).toEqual([]);
    expect(new Set(BANTER_NOUNS).size).toBe(BANTER_NOUNS.length);
    expect(new Set(BANTER_ADJECTIVES).size).toBe(BANTER_ADJECTIVES.length);
    expect(new Set(BANTER_VERBS).size).toBe(BANTER_VERBS.length);
  });

  it("starts after three seconds, and changes every ten", () => {
    expect(BANTER_DELAY_MS).toBe(3_000);
    expect(BANTER_INTERVAL_MS).toBe(10_000);
  });
});

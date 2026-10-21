import { describe, expect, it } from "vitest";

import { didYouKnowFacts, factOfTheDay, randomFact } from "@/lib/facts";

const DAY_MS = 24 * 60 * 60 * 1000;

describe("didYouKnowFacts", () => {
  it("has at least a dozen distinct facts", () => {
    const facts = didYouKnowFacts();
    expect(facts.length).toBeGreaterThanOrEqual(12);
    expect(new Set(facts.map((fact) => fact.text)).size).toBe(facts.length);
  });

  it("links each fact that has a link to GitHub, the docs, the blog, the web site or npm, with a label", () => {
    const links = didYouKnowFacts().flatMap((fact) => (fact.link ? [fact.link] : []));
    expect(links.length).toBeGreaterThan(0);
    for (const link of links) {
      expect(link.url).toMatch(
        /^https:\/\/(github\.com\/smarter-sh(\/|$)|docs\.smarter\.sh\/|blog\.smarter\.sh\/|smarter\.sh\/|www\.npmjs\.com\/)/,
      );
      expect(link.label).not.toBe("");
    }
  });
});

describe("randomFact", () => {
  it("picks a fact from the random number, within range", () => {
    const facts = didYouKnowFacts();
    expect(randomFact(() => 0)).toEqual(facts[0]);
    expect(randomFact(() => 0.999)).toEqual(facts[facts.length - 1]);
  });

  it("uses Math.random by default", () => {
    expect(didYouKnowFacts()).toContainEqual(randomFact());
  });
});

describe("factOfTheDay", () => {
  const facts = didYouKnowFacts();

  it("is the same fact from midnight to midnight UTC", () => {
    const midnight = new Date("2026-10-20T00:00:00Z");
    const lastMoment = new Date(midnight.getTime() + DAY_MS - 1);
    expect(factOfTheDay(lastMoment)).toEqual(factOfTheDay(midnight));
  });

  it("goes on to the next fact the next day, and back to the first after the last", () => {
    const first = new Date(facts.length * DAY_MS * 1000);
    expect(factOfTheDay(first)).toEqual(facts[0]);
    expect(factOfTheDay(new Date(first.getTime() + DAY_MS))).toEqual(facts[1]);
    expect(factOfTheDay(new Date(first.getTime() - DAY_MS))).toEqual(facts[facts.length - 1]);
  });

  it("picks a fact for a date before 1970", () => {
    expect(facts).toContainEqual(factOfTheDay(new Date("1969-07-20T20:17:00Z")));
  });

  it("uses today by default", () => {
    expect(factOfTheDay()).toEqual(factOfTheDay(new Date()));
  });
});

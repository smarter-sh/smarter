import { describe, expect, it } from "vitest";

import { didYouKnowFacts } from "@/lib/facts";
import { slackEscape, slackMessage } from "@/lib/slack";

describe("slackEscape", () => {
  it("escapes &, < and >", () => {
    expect(slackEscape("a < b && c > d")).toBe("a &lt; b &amp;&amp; c &gt; d");
  });
});

describe("slackMessage", () => {
  it("has the title, the fact and its link", () => {
    const message = slackMessage({
      text: "Smarter has <many> facts & figures.",
      link: { label: "Read <more>", url: "https://docs.smarter.sh/en/latest/" },
    });
    expect(message).toBe(
      ":bulb: *Did you know?*\nSmarter has &lt;many&gt; facts &amp; figures.\n<https://docs.smarter.sh/en/latest/|Read &lt;more&gt;>",
    );
  });

  it("leaves out the link of a fact that has none", () => {
    expect(slackMessage({ text: "Smarter's first commit was made in February 2023." })).toBe(
      ":bulb: *Did you know?*\nSmarter's first commit was made in February 2023.",
    );
  });

  it("formats every fact", () => {
    for (const fact of didYouKnowFacts()) {
      expect(slackMessage(fact)).toContain(slackEscape(fact.text));
    }
  });
});

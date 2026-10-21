import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { factOfTheDay } from "@smarter/didyouknow";

import DidYouKnow from "@/components/DidYouKnow/Component";

describe("DidYouKnow", () => {
  it("shows the fact of the day, the same one as the web console's title bar", () => {
    const date = new Date("2026-10-21T12:00:00Z");
    render(<DidYouKnow date={date} />);
    const card = screen.getByRole("complementary", { name: "Did you know?" });
    expect(card).toHaveClass("card");
    expect(card).toHaveTextContent(factOfTheDay(date).text);
  });

  it("shows another fact on another day", () => {
    const today = new Date("2026-10-21T12:00:00Z");
    const tomorrow = new Date("2026-10-22T12:00:00Z");
    render(<DidYouKnow date={tomorrow} />);
    expect(screen.getByRole("complementary")).toHaveTextContent(factOfTheDay(tomorrow).text);
    expect(factOfTheDay(tomorrow).text).not.toBe(factOfTheDay(today).text);
  });

  it("links to more, in a new tab, when the fact has a link", () => {
    // a day whose fact has a link.
    const start = new Date("2026-10-21T12:00:00Z").getTime();
    const date = [...Array(60).keys()]
      .map((day) => new Date(start + day * 86_400_000))
      .find((day) => factOfTheDay(day).link) as Date;
    render(<DidYouKnow date={date} />);
    const link = within(screen.getByRole("complementary")).getByRole("link", {
      name: factOfTheDay(date).link?.label,
    });
    expect(link).toHaveAttribute("href", factOfTheDay(date).link?.url);
    expect(link).toHaveAttribute("target", "_blank");
  });
});

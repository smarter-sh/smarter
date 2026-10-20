import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import App from "@/App";
import { factOfTheDay } from "@/lib/facts";

describe("App", () => {
  it("shows the fact of the day, styled for the title bar", () => {
    const date = new Date("2026-10-20T12:00:00Z");
    render(<App date={date} />);
    const note = screen.getByRole("complementary", { name: "Did you know?" });
    expect(note).toHaveClass("smarter-didyouknow-header");
    expect(note).toHaveTextContent(factOfTheDay(date).text);
  });

  it("shows today's fact by default", () => {
    render(<App />);
    expect(screen.getByRole("complementary", { name: "Did you know?" })).toHaveTextContent(factOfTheDay().text);
  });
});

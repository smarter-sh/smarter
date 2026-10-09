import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import WhatsNew from "@/components/WhatsNew/Component";

// Checks the list's invariants rather than its content, so that adding a
// feature to the top of the list does not break the test.
describe("WhatsNew", () => {
  it("links every feature to its documentation", () => {
    render(<WhatsNew />);
    const links = screen.getAllByRole("link");
    expect(links.length).toBeGreaterThan(0);
    for (const link of links) {
      expect(link).not.toBeEmptyDOMElement();
      expect(link).toHaveAttribute("href", expect.stringMatching(/^https:\/\/docs\.smarter\.sh\/.+\.html$/));
    }
  });

  it("lists the newest features first", () => {
    render(<WhatsNew />);
    const versions = screen
      .getAllByText(/^\d+\.\d+$/)
      .map((badge) => badge.textContent!.split(".").map(Number))
      .map(([major, minor]) => major * 1000 + minor);
    expect(versions.length).toBeGreaterThan(1);
    expect(versions).toEqual([...versions].sort((a, b) => b - a));
  });
});

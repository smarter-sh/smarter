import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import WhatsNew from "./Component";

describe("WhatsNew", () => {
  it("lists the newest feature first, linked to its documentation", () => {
    render(<WhatsNew />);
    const links = screen.getAllByRole("link");
    expect(links[0]).toHaveTextContent("Custom Domains");
    expect(links[0]).toHaveAttribute("href", "https://docs.smarter.sh/smarter-resources/smarter-custom-domain.html");
  });
});

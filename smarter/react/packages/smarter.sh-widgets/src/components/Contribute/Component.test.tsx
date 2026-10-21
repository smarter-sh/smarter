import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import Contribute from "@/components/Contribute/Component";

describe("Contribute", () => {
  it("lists ways to help, and links to the contributing guide and the open issues", () => {
    render(<Contribute />);
    const contribute = screen.getByRole("region", { name: "Contribute" });

    expect(
      within(within(contribute).getByRole("list", { name: "Ways to help" })).getAllByRole("listitem"),
    ).toHaveLength(4);
    expect(within(contribute).getByRole("link", { name: "Contributing guide" })).toHaveAttribute(
      "href",
      "https://docs.smarter.sh/en/latest/smarter-framework/guides/contributing.html",
    );
    expect(within(contribute).getByRole("link", { name: "Open issues" })).toHaveAttribute(
      "href",
      "https://github.com/smarter-sh/smarter/issues",
    );
    expect(within(contribute).getByRole("link", { name: "GitHub Stars" })).toHaveAttribute(
      "href",
      "https://github.com/smarter-sh/smarter/stargazers",
    );
  });
});

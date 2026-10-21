import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import Cli from "@/components/Cli/Component";

describe("Cli", () => {
  it("shows an example session, and links to the download and the documentation", () => {
    render(<Cli />);
    const cli = screen.getByRole("region", { name: "CLI" });

    expect(within(cli).getByLabelText("Example CLI session")).toHaveTextContent("smarter apply -f llmclient.yaml");
    expect(within(cli).getByRole("link", { name: "Download" })).toHaveAttribute("href", "https://smarter.sh/cli/");
    expect(within(cli).getByRole("link", { name: "Documentation" })).toHaveAttribute(
      "href",
      "https://docs.smarter.sh/en/latest/smarter-framework/smarter-cli.html",
    );
  });

  it("is as wide as the page sets", () => {
    render(<Cli className="col-12" />);
    expect(screen.getByRole("region", { name: "CLI" })).toHaveClass("col-12");
    expect(screen.getByRole("region", { name: "CLI" })).not.toHaveClass("col-xl-4");
  });
});

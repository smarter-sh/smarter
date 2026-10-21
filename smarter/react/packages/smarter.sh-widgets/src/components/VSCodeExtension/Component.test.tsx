import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import VSCodeExtension from "@/components/VSCodeExtension/Component";

const MARKETPLACE = "https://marketplace.visualstudio.com/items?itemName=Querium.smarter-manifest";

describe("VSCodeExtension", () => {
  it("lists the features, and links to the marketplace and the documentation", () => {
    render(<VSCodeExtension />);
    const card = screen.getByLabelText("VS Code Extension");

    expect(within(within(card).getByRole("list", { name: "Features" })).getAllByRole("listitem")).toHaveLength(4);
    expect(within(card).getByRole("link", { name: "Install" })).toHaveAttribute("href", MARKETPLACE);
    expect(within(card).getByRole("link", { name: "Documentation" })).toHaveAttribute(
      "href",
      "https://docs.smarter.sh/en/latest/smarter-framework/vs-code-extension.html",
    );
  });

  it("shows the extension flagging a misspelled key", () => {
    render(<VSCodeExtension />);
    expect(screen.getByRole("note")).toHaveTextContent(
      "Unknown key 'descripton' in metadata. Did you mean 'description'?",
    );
  });
});

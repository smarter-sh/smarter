import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import Integrations from "@/components/Integrations/Component";

const DOCS = "https://docs.smarter.sh/en/latest/smarter-framework";

describe("Integrations", () => {
  it("links each integration's logo to its documentation", () => {
    render(<Integrations />);
    const integrations = screen.getByRole("region", { name: "Integrations" });

    for (const [name, page] of [
      ["WordPress", "smarter-wordpress"],
      ["Drupal", "smarter-drupal"],
      ["Shopify", "smarter-shopify"],
      ["Google Tag Manager", "smarter-gtm"],
      ["Docusaurus", "smarter-docs-sites"],
      ["MkDocs", "smarter-docs-sites"],
      ["Sphinx", "smarter-docs-sites"],
      ["VitePress", "smarter-docs-sites"],
    ]) {
      expect(within(integrations).getByRole("link", { name })).toHaveAttribute("href", `${DOCS}/${page}.html`);
    }
  });

  it("links to the embedding guide and the source code", () => {
    render(<Integrations />);
    expect(screen.getByRole("link", { name: "Embedding guide" })).toHaveAttribute(
      "href",
      `${DOCS}/smarter-chat/embedding.html`,
    );
    expect(screen.getByRole("link", { name: "Integrations source code" })).toHaveAttribute(
      "href",
      "https://github.com/smarter-sh",
    );
  });

  it("is as wide as the page sets", () => {
    render(<Integrations className="col-12" />);
    expect(screen.getByRole("region", { name: "Integrations" })).toHaveClass("col-12");
    expect(screen.getByRole("region", { name: "Integrations" })).not.toHaveClass("col-xl-4");
  });
});

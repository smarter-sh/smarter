import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import Extensions from "@/components/Extensions/Component";

const DOCS = "https://docs.smarter.sh/en/latest";

describe("Extensions", () => {
  it("shows the official extensions, and a manifest that uses one", () => {
    render(<Extensions />);
    const extensions = screen.getByRole("region", { name: "Extensions" });

    const official = within(extensions).getByRole("list", { name: "Official extensions" });
    expect(within(official).getAllByRole("listitem")).toHaveLength(3);
    expect(within(extensions).getByLabelText("An LLMClient manifest that uses an extension")).toHaveTextContent(
      "- weather",
    );
  });

  it("links each official extension to its GitHub repository", () => {
    render(<Extensions />);
    const official = screen.getByRole("list", { name: "Official extensions" });
    for (const [name, slug] of [
      [/Weather/, "weather"],
      [/^Calculator/, "calculator"],
      [/Date Calculator/, "date-calculator"],
    ] as const) {
      expect(within(official).getByRole("link", { name })).toHaveAttribute(
        "href",
        `https://github.com/smarter-sh/smarter-extension-${slug}`,
      );
    }
  });

  it("links to the documentation, the registry and the guide to building one", () => {
    render(<Extensions />);
    for (const [name, href] of [
      ["How extensions work", `${DOCS}/smarter-platform/extensions.html`],
      ["Browse the registry", "https://github.com/smarter-sh/extensions-registry"],
      [/^Build one →$/, `${DOCS}/smarter-framework/smarter-extensions.html`],
    ]) {
      expect(screen.getByRole("link", { name })).toHaveAttribute("href", href);
    }
  });

  it("stays light in the web console's dark mode, like the other light widgets", () => {
    render(<Extensions />);
    expect(screen.getByRole("region", { name: "Extensions" })).toHaveAttribute("data-bs-theme", "light");
  });
});

import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import Sdk from "@/components/Sdk/Component";

describe("Sdk", () => {
  it("links each SDK to its package registry, and shows its install command", () => {
    render(<Sdk />);
    const sdks = screen.getByRole("region", { name: "SDK" });

    for (const [name, href, install] of [
      [
        "smarter-chat NPM Package",
        "https://www.npmjs.com/package/@smarter.sh/ui-chat",
        "npm install @smarter.sh/ui-chat",
      ],
      ["Node.js SDK", "https://www.npmjs.com/package/@smarter.sh/api", "npm install @smarter.sh/api"],
      ["Python PyPi Library", "https://pypi.org/project/smarter-api/", "pip install smarter-api"],
      [
        "Go SDK",
        "https://pkg.go.dev/github.com/smarter-sh/smarter-golang",
        "go get github.com/smarter-sh/smarter-golang",
      ],
    ]) {
      expect(within(sdks).getByRole("link", { name })).toHaveAttribute("href", href);
      expect(within(sdks).getByText(install)).toBeInTheDocument();
    }
  });

  it("links to the documentation and the source code", () => {
    render(<Sdk />);
    expect(screen.getByRole("link", { name: "Documentation" })).toHaveAttribute(
      "href",
      "https://docs.smarter.sh/en/latest/smarter-framework/apis-and-sdks.html",
    );
    expect(screen.getByRole("link", { name: "API reference" })).toHaveAttribute("href", "/docs/openapi/");
    expect(screen.getByRole("link", { name: "SDK source code" })).toHaveAttribute(
      "href",
      "https://github.com/smarter-sh",
    );
  });
});

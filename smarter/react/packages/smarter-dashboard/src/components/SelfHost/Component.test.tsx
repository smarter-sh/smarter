import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import SelfHost from "@/components/SelfHost/Component";

describe("SelfHost", () => {
  it("shows the path from a laptop to production, and links each step", () => {
    render(<SelfHost />);
    const selfHost = screen.getByRole("region", { name: "Self Host" });

    for (const [name, href] of [
      ["Docker", "https://github.com/smarter-sh/smarter-deploy"],
      ["Kubernetes", "https://artifacthub.io/packages/helm/project-smarter/smarter"],
      ["Terraform", "https://github.com/smarter-sh/smarter-infrastructure"],
    ]) {
      expect(within(selfHost).getByRole("link", { name: new RegExp(name) })).toHaveAttribute("href", href);
    }
    expect(within(selfHost).getByRole("link", { name: "Installation Guide" })).toHaveAttribute(
      "href",
      "https://docs.smarter.sh/en/latest/smarter-platform/installation.html",
    );
  });
});

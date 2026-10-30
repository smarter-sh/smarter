import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { extensionObjects, sessionContext } from "@/mocks/fixtures";

import ExtensionDetailView from "@/components/ExtensionDetailView/Component";

describe("ExtensionDetailView", () => {
  it("shows an enabled extension from the registry, read-only", () => {
    const extension = extensionObjects[0];
    render(<ExtensionDetailView sessionContext={sessionContext} object={extension} onRequery={() => {}} />);
    expect(screen.getByText(extension.description)).toBeInTheDocument();
    expect(screen.getByText("Enabled")).toBeInTheDocument();
    for (const title of ["Extension", "Installation"]) {
      expect(screen.getByRole("heading", { name: title })).toBeInTheDocument();
    }
    expect(screen.getByText("Weather")).toBeInTheDocument();
    expect(screen.getByText("weather")).toBeInTheDocument();
    expect(screen.getByText("Official Smarter Extension")).toBeInTheDocument();
    expect(screen.getByText("The Smarter Extension registry")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: new RegExp(extension.homepage ?? "") })).toHaveAttribute(
      "href",
      extension.homepage,
    );
    expect(screen.queryByRole("group", { name: "Actions" })).not.toBeInTheDocument();
  });

  it("shows a disabled, uploaded extension without a homepage", () => {
    render(<ExtensionDetailView sessionContext={sessionContext} object={extensionObjects[1]} onRequery={() => {}} />);
    expect(screen.getByText("Disabled")).toBeInTheDocument();
    expect(screen.getByText("An uploaded archive")).toBeInTheDocument();
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });
});

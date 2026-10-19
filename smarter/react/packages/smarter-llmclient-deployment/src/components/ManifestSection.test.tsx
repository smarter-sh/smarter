import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import ManifestSection from "@/components/ManifestSection";
import { MANIFEST_YAML, notDeployedPage, publicPage, workbenchPage } from "@/mocks/fixtures";

describe("ManifestSection", () => {
  it("shows the manifest, highlighted, as text", () => {
    render(<ManifestSection page={workbenchPage} />);
    const terminal = screen.getByRole("group", { name: "stackademy.yaml" });
    expect(terminal).toHaveTextContent(MANIFEST_YAML, { normalizeWhitespace: false });
    expect(within(terminal).getByText("apiVersion")).toHaveClass("yaml-key");
    // html in the manifest is text.
    expect(within(terminal).getByText("Answer in <b>one</b> sentence.", { exact: false })).toHaveClass("yaml-string");
    expect(screen.queryByRole("link", { name: "Open it in the workbench" })).not.toBeInTheDocument();
  });

  it("links the public page to the workbench", () => {
    render(<ManifestSection page={publicPage} />);
    expect(screen.getByRole("link", { name: "Open it in the workbench" })).toHaveAttribute(
      "href",
      publicPage.llmclient.workbenchUrl,
    );
  });

  it("without a manifest", () => {
    render(<ManifestSection page={notDeployedPage} />);
    expect(screen.queryByRole("group", { name: "stackademy.yaml" })).not.toBeInTheDocument();
    expect(screen.getByRole("group", { name: "smarter cli" })).toBeInTheDocument();
  });
});

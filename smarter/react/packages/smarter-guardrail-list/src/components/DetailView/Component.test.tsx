import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { makeObject, sessionContext } from "@/mocks/fixtures";

import DetailView from "@/components/DetailView/Component";

describe("DetailView", () => {
  it("shows the guardrail's description, sections and metadata", () => {
    render(<DetailView sessionContext={sessionContext} object={makeObject(1)} onRequery={() => {}} />);
    expect(screen.getByText("An example, number 1.")).toBeInTheDocument();
    expect(screen.getByText("Active")).toBeInTheDocument();
    expect(screen.getByText("Enforced")).toBeInTheDocument();
    for (const title of ["Classification", "Detection", "Response", "Metadata"]) {
      expect(screen.getByRole("heading", { name: title })).toBeInTheDocument();
    }
    expect(screen.getByText(/"credit_card"/)).toBeInTheDocument();
    expect(screen.getByText("[REDACTED {label}]")).toBeInTheDocument();
    expect(screen.getByText("admin@example.com")).toBeInTheDocument();
  });

  it("shows a monitoring guardrail without a configuration", () => {
    render(
      <DetailView
        sessionContext={sessionContext}
        object={makeObject(2, { mode: "monitor", isActive: false, config: null })}
        onRequery={() => {}}
      />,
    );
    expect(screen.getByText("Inactive")).toBeInTheDocument();
    expect(screen.getByText("Monitor only")).toBeInTheDocument();
    expect(screen.queryByText(/"credit_card"/)).not.toBeInTheDocument();
  });

  it("narrows the list by a tag that is clicked", async () => {
    const onTag = vi.fn();
    render(
      <DetailView
        sessionContext={sessionContext}
        object={makeObject(1)}
        onRequery={() => {}}
        filtering={{ tags: [], annotations: [], onTag, onAnnotation: vi.fn() }}
      />,
    );
    await userEvent.setup().click(screen.getByRole("button", { name: "example" }));
    expect(onTag).toHaveBeenCalledWith("example");
  });
});

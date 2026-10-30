import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { makeObject, sessionContext } from "@/mocks/fixtures";

import DetailView from "@/components/DetailView/Component";

describe("DetailView", () => {
  it("shows the authtoken's description, status, actions and metadata", () => {
    const authtoken = makeObject(1);
    render(<DetailView sessionContext={sessionContext} object={authtoken} onRequery={() => {}} />);
    expect(screen.getByText("An example, number 1.")).toBeInTheDocument();
    expect(screen.getAllByText("Active").length).toBeGreaterThan(0);
    expect(screen.getByRole("group", { name: "Actions" })).toBeInTheDocument();
    for (const title of ["Status", "Metadata"]) {
      expect(screen.getByRole("heading", { name: title })).toBeInTheDocument();
    }
    expect(screen.getByText("Last used")).toBeInTheDocument();
    expect(screen.getByText("Shown only once, when the key is created.")).toBeInTheDocument();
    expect(screen.getByText(authtoken.id)).toBeInTheDocument();
    expect(screen.getByText("admin@example.com")).toBeInTheDocument();
  });

  it("shows an inactive authtoken that has never been used", () => {
    render(
      <DetailView
        sessionContext={sessionContext}
        object={makeObject(2, { isActive: false, lastUsedAt: null })}
        onRequery={() => {}}
      />,
    );
    expect(screen.getByText("Inactive")).toBeInTheDocument();
    // the Active field says No, and Last used has no value.
    expect(screen.getByText("No")).toBeInTheDocument();
    expect(screen.getAllByText("No value").length).toBeGreaterThan(0);
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

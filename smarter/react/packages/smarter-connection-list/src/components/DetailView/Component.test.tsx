import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { makeObject, sessionContext } from "@/mocks/fixtures";

import DetailView from "@/components/DetailView/Component";

describe("DetailView", () => {
  it("shows the connection's description, sections and metadata", () => {
    render(<DetailView sessionContext={sessionContext} object={makeObject(1)} onRequery={() => {}} />);
    expect(screen.getByText("An example, number 1.")).toBeInTheDocument();
    expect(screen.getByText("Ready", { selector: ".badge" })).toBeInTheDocument();
    for (const title of ["Connection", "Metadata"]) {
      expect(screen.getByRole("heading", { name: title })).toBeInTheDocument();
    }
    expect(screen.getByText("SqlConnection")).toBeInTheDocument();
    expect(screen.getAllByText("SQL database").length).toBe(2);
    expect(screen.getByText("admin@example.com")).toBeInTheDocument();
  });

  it("shows an api connection that is not ready, and a kind that it doesn't know", () => {
    const { rerender } = render(
      <DetailView
        sessionContext={sessionContext}
        object={makeObject(2, { kind: "ApiConnection", ready: false })}
        onRequery={() => {}}
      />,
    );
    expect(screen.getByText("Not ready")).toBeInTheDocument();
    expect(screen.getAllByText("REST API").length).toBe(2);

    rerender(
      <DetailView
        sessionContext={sessionContext}
        object={makeObject(2, { kind: "OtherConnection" as never })}
        onRequery={() => {}}
      />,
    );
    expect(screen.getAllByText("OtherConnection").length).toBeGreaterThan(0);
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

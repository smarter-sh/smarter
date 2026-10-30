import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { makeObject, sessionContext } from "@/mocks/fixtures";

import DetailView from "@/components/DetailView/Component";

describe("DetailView", () => {
  it("shows the compute's description, node, node group and metadata", () => {
    render(<DetailView sessionContext={sessionContext} object={makeObject(1)} onRequery={() => {}} />);
    expect(screen.getByText("An example, number 1.")).toBeInTheDocument();
    for (const title of ["Node", "Node group", "Metadata"]) {
      expect(screen.getByRole("heading", { name: title })).toBeInTheDocument();
    }
    expect(screen.getByText("g6.2xlarge")).toBeInTheDocument();
    expect(screen.getByText("1 × L4, 24 GB")).toBeInTheDocument();
    expect(screen.getByText("$0.98/hr")).toBeInTheDocument();
    expect(screen.getByText("smarter-alpha-1-gpu-l4-1x")).toBeInTheDocument();
    expect(screen.getByText("ACTIVE")).toBeInTheDocument();
    expect(screen.getByText("admin@example.com")).toBeInTheDocument();
  });

  it("shows a CPU node whose node group is not created yet", () => {
    render(
      <DetailView
        sessionContext={sessionContext}
        object={makeObject(2, { gpuCount: 0, pricePerHour: null, nodegroupStatus: "absent", statusMessage: "" })}
        onRequery={() => {}}
      />,
    );
    expect(screen.getByText("CPU only")).toBeInTheDocument();
    expect(screen.getByText("Not created yet")).toBeInTheDocument();
    expect(screen.queryByText(/\/hr$/)).not.toBeInTheDocument();
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

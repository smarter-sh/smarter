import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { makeObject, sessionContext } from "@/mocks/fixtures";

import DetailView from "@/components/DetailView/Component";

describe("DetailView", () => {
  it("shows the orchestrator's description, sections and metadata", () => {
    render(<DetailView sessionContext={sessionContext} object={makeObject(1)} onRequery={() => {}} />);
    expect(screen.getByText("An example, number 1.")).toBeInTheDocument();
    expect(screen.getByText("Active", { selector: ".badge" })).toBeInTheDocument();
    for (const title of ["Orchestration", "Harnesses", "Metadata"]) {
      expect(screen.getByRole("heading", { name: title })).toBeInTheDocument();
    }
    expect(screen.getByText("sequential")).toBeInTheDocument();
    expect(screen.getByText("planner", { selector: "code" })).toBeInTheDocument();
    expect(screen.getByText("writer")).toBeInTheDocument();
    expect(screen.getByText("admin@example.com")).toBeInTheDocument();
  });

  it("lists the harnesses in the order in which they run, with their overrides", () => {
    render(
      <DetailView
        sessionContext={sessionContext}
        object={makeObject(2, {
          isActive: false,
          harnesses: [
            { llmClientName: "second", role: "critic", executionOrder: 2, isActive: false, config: { temperature: 0 } },
            { llmClientName: "first", role: "planner", executionOrder: 1, isActive: true, config: {} },
          ],
        })}
        onRequery={() => {}}
      />,
    );
    expect(screen.getByText("Inactive")).toBeInTheDocument();
    const rows = within(screen.getByRole("table")).getAllByRole("row");
    expect(rows[1]).toHaveTextContent("first");
    expect(rows[2]).toHaveTextContent("second");
    expect(rows[2]).toHaveTextContent('"temperature": 0');
  });

  it("shows an orchestrator without harnesses", () => {
    render(
      <DetailView sessionContext={sessionContext} object={makeObject(3, { harnesses: [] })} onRequery={() => {}} />,
    );
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
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

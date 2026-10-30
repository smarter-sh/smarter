import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { makeObject, sessionContext } from "@/mocks/fixtures";

import DetailView from "@/components/DetailView/Component";

describe("DetailView", () => {
  it("shows the LLMHost's description, status, sections and metadata", () => {
    render(<DetailView sessionContext={sessionContext} object={makeObject(1)} onRequery={() => {}} />);
    expect(screen.getByText("An example, number 1.")).toBeInTheDocument();
    expect(screen.getAllByText("Active").length).toBeGreaterThan(0);
    expect(screen.queryByText("Disabled")).not.toBeInTheDocument();
    for (const title of ["Model", "Serving", "Compute", "Deployment", "Metadata"]) {
      expect(screen.getByRole("heading", { name: title })).toBeInTheDocument();
    }
    expect(screen.getByText("meta-llama/Llama-3.2-3B-Instruct")).toBeInTheDocument();
    expect(screen.getByText("Function calling")).toBeInTheDocument();
    expect(screen.queryByText("Vision")).not.toBeInTheDocument();
    expect(screen.getByText("$0.98/hr")).toBeInTheDocument();
    expect(screen.getByText("http://example.llmhost.svc.cluster.local:8000")).toBeInTheDocument();
    expect(screen.getByText("admin@example.com")).toBeInTheDocument();
  });

  it("shows a failed, disabled LLMHost and its public URL", () => {
    render(
      <DetailView
        sessionContext={sessionContext}
        object={makeObject(2, {
          status: "error",
          statusMessage: "The pod could not pull its image.",
          isActive: false,
          costPerHour: null,
          publicUrl: "https://llm.example.com",
        })}
        onRequery={() => {}}
      />,
    );
    expect(screen.getAllByText("Error").length).toBeGreaterThan(0);
    expect(screen.getByText("Disabled")).toBeInTheDocument();
    expect(screen.getByText("The pod could not pull its image.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /https:\/\/llm\.example\.com/ })).toHaveAttribute(
      "href",
      "https://llm.example.com",
    );
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

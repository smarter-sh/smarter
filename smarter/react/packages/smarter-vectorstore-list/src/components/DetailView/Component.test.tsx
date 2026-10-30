import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { makeObject, sessionContext } from "@/mocks/fixtures";

import DetailView from "@/components/DetailView/Component";

describe("DetailView", () => {
  it("shows the vectorstore's description, sections and metadata", () => {
    render(<DetailView sessionContext={sessionContext} object={makeObject(1)} onRequery={() => {}} />);
    expect(screen.getByText("An example, number 1.")).toBeInTheDocument();
    for (const title of ["Database", "Embeddings", "Contents", "Lifecycle", "Metadata"]) {
      expect(screen.getByRole("heading", { name: title })).toBeInTheDocument();
    }
    expect(screen.getByText("Qdrant")).toBeInTheDocument();
    expect(screen.getByText("Self-hosted")).toBeInTheDocument();
    expect(screen.getByText("text-embedding-3-small")).toBeInTheDocument();
    expect(screen.getByText((1200).toLocaleString())).toBeInTheDocument();
    expect(screen.getAllByText("Ready").length).toBeGreaterThan(0);
    expect(screen.getByText("admin@example.com")).toBeInTheDocument();
  });

  it("shows a managed, failed vectorstore, its statistics, and its secret's name only", () => {
    render(
      <DetailView
        sessionContext={sessionContext}
        object={makeObject(2, {
          backend: "pinecone",
          hosting: "managed",
          apiKeySecret: "pinecone_api_key",
          status: "failed",
          statusMessage: "Quota exceeded.",
          stats: { namespaces: 1 },
        })}
        onRequery={() => {}}
      />,
    );
    expect(screen.getByText("Pinecone")).toBeInTheDocument();
    expect(screen.getByText("Managed")).toBeInTheDocument();
    expect(screen.getAllByText("Failed").length).toBeGreaterThan(0);
    expect(screen.getByText("Quota exceeded.")).toBeInTheDocument();
    expect(screen.getByText("pinecone_api_key")).toBeInTheDocument();
    expect(screen.getByLabelText("JSON")).toHaveTextContent(/"namespaces": 1/);
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

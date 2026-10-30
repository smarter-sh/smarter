import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { makeObject, sessionContext } from "@/mocks/fixtures";

import DetailView from "@/components/DetailView/Component";

describe("DetailView", () => {
  it("shows the vectorsearch's description, sections and metadata", () => {
    render(<DetailView sessionContext={sessionContext} object={makeObject(1)} onRequery={() => {}} />);
    expect(screen.getByText("An example, number 1.")).toBeInTheDocument();
    expect(screen.getByText("Enabled")).toBeInTheDocument();
    for (const title of ["Source", "Retrieval", "Metadata"]) {
      expect(screen.getByRole("heading", { name: title })).toBeInTheDocument();
    }
    expect(screen.getByText("example_vectorstore")).toBeInTheDocument();
    expect(screen.getByText("Similarity")).toBeInTheDocument();
    expect(screen.getByText("4")).toBeInTheDocument();
    expect(screen.queryByText("Score threshold")).not.toBeInTheDocument();
    expect(screen.queryByText("Diversity (lambda)")).not.toBeInTheDocument();
    expect(screen.getByText("admin@example.com")).toBeInTheDocument();
  });

  it("shows a disabled MMR vectorsearch with a metadata filter and a Secret", () => {
    render(
      <DetailView
        sessionContext={sessionContext}
        object={makeObject(2, {
          isEnabled: false,
          searchType: "mmr",
          fetchK: 20,
          lambdaMult: 0.5,
          metadataFilter: { source: "faq" },
          authSecret: "vectorstore_credentials",
        })}
        onRequery={() => {}}
      />,
    );
    expect(screen.getByText("Disabled")).toBeInTheDocument();
    expect(screen.getByText("Maximal marginal relevance (MMR)")).toBeInTheDocument();
    expect(screen.getByText("20")).toBeInTheDocument();
    expect(screen.getByText("0.5")).toBeInTheDocument();
    expect(screen.getByLabelText("JSON")).toHaveTextContent(/"source": "faq"/);
    expect(screen.getByText("vectorstore_credentials")).toBeInTheDocument();
  });

  it("shows the score threshold of a threshold search", () => {
    render(
      <DetailView
        sessionContext={sessionContext}
        object={makeObject(3, { searchType: "similarity_score_threshold", scoreThreshold: 0.75 })}
        onRequery={() => {}}
      />,
    );
    expect(screen.getByText("Similarity, above a score threshold")).toBeInTheDocument();
    expect(screen.getByText("0.75")).toBeInTheDocument();
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

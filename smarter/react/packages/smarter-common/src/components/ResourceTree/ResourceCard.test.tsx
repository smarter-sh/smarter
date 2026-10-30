import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import ResourceCard from "./ResourceCard";
import { leafTree, lockedTree, stackademyTree } from "../../mocks/resourceTree";

describe("ResourceCard", () => {
  it("shows the kind, the name and the owner, and opens the manifest in a new tab", () => {
    const secret = stackademyTree.children[2].children[0];
    render(<ResourceCard node={secret} />);
    const card = screen.getByRole("article", { name: "Secret openai_api_key" });
    expect(card).toHaveTextContent("Secret");
    expect(card).toHaveTextContent("An encrypted credential");
    expect(card).toHaveTextContent("Owner: Ada Lovelace (ada)");
    const link = screen.getByRole("link", { name: "openai_api_key" });
    expect(link).toHaveAttribute("href", "/secret/secrets/rMTAwMDAxMQx/");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
    expect(link).toHaveAttribute("title", "Open the manifest of openai_api_key in a new tab");
    expect(screen.getByTestId("architecture-card-icon")).toHaveClass("ki-lock-2");
  });

  it("links the kind to its documentation", () => {
    render(<ResourceCard node={leafTree} isRoot />);
    expect(screen.getByRole("link", { name: "About LLMClient, in the documentation" })).toHaveAttribute(
      "href",
      "https://docs.smarter.sh/en/latest/smarter-resources/smarter-llmclient.html",
    );
    expect(screen.getByRole("article")).toHaveClass("architecture-card-root", "architecture-card-primary");
  });

  it("locks a resource that the user can't read", () => {
    render(<ResourceCard node={lockedTree.children[0]} />);
    const card = screen.getByRole("article", { name: "Guardrail guardrail-rMTAwMDA5OQx" });
    expect(card).toHaveClass("architecture-card-locked");
    expect(card).toHaveTextContent("You can't read this resource");
    expect(card).toHaveTextContent("guardrail-rMTAwMDA5OQx");
    expect(card).not.toHaveTextContent("Owner");
    expect(screen.getByTestId("architecture-card-icon")).toHaveClass("ki-lock-3");
    // only the documentation's link: the card opens nothing.
    expect(screen.getAllByRole("link")).toHaveLength(1);
  });

  it("opens nothing for a resource without a manifest page", () => {
    render(<ResourceCard node={{ ...leafTree, url: null, owner: null }} />);
    expect(screen.queryByRole("link", { name: "hello_world" })).not.toBeInTheDocument();
    expect(screen.getByText("hello_world")).toBeInTheDocument();
    expect(screen.getByRole("article")).not.toHaveTextContent("Owner");
  });
});

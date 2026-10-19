import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import App from "@/App";
import { DOCS_URLS } from "@/lib/const";
import { leafArchitecture, lockedArchitecture, stackademyArchitecture } from "@/mocks/fixtures";

describe("App", () => {
  it("introduces SAM resources, their manifests, and the LLMClient's tree, with links to the documentation", () => {
    render(<App architecture={stackademyArchitecture} />);
    expect(screen.getByRole("heading", { level: 2, name: "How this LLMClient is built" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Everything is a SAM resource" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Edit any manifest here" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "An LLMClient is a tree" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Smarter Application Manifests" })).toHaveAttribute(
      "href",
      DOCS_URLS.manifests,
    );
    expect(screen.getByRole("link", { name: "The web console" })).toHaveAttribute("href", DOCS_URLS.webConsole);
    expect(screen.getByRole("link", { name: "Dependency trees" })).toHaveAttribute("href", DOCS_URLS.dependencyTrees);
    expect(screen.getByRole("link", { name: "Who owns a resource, and who may read it" })).toHaveAttribute(
      "href",
      DOCS_URLS.ownership,
    );
  });

  it("draws every resource as a card, and counts them", () => {
    render(<App architecture={stackademyArchitecture} />);
    const tree = screen.getByRole("list", { name: "The resources that this LLMClient is built from" });
    // the Provider, and its Secret, are drawn under the LLMClient and under its plugin.
    expect(within(tree).getAllByRole("article")).toHaveLength(10);
    expect(within(tree).getAllByRole("article", { name: "Provider openai" })).toHaveLength(2);
    expect(screen.getByRole("status")).toHaveTextContent("8 resources · 3 levels deep");
  });

  it("hides what a resource uses, and shows it again", async () => {
    const user = userEvent.setup();
    render(<App architecture={stackademyArchitecture} />);
    const hide = screen.getByRole("button", { name: "Hide what stackademy_sql uses" });
    expect(hide).toHaveAttribute("aria-expanded", "true");
    await user.click(hide);
    expect(screen.queryByRole("article", { name: "SqlConnection smarter_test_db" })).not.toBeInTheDocument();
    expect(screen.getByText("2 more")).toBeInTheDocument();
    const show = screen.getByRole("button", { name: "Show what stackademy_sql uses" });
    expect(show).toHaveAttribute("aria-expanded", "false");
    await user.click(show);
    expect(screen.getByRole("article", { name: "SqlConnection smarter_test_db" })).toBeInTheDocument();
  });

  it("collapses and expands every resource", async () => {
    const user = userEvent.setup();
    render(<App architecture={stackademyArchitecture} />);
    const expand = screen.getByRole("button", { name: "Expand all" });
    const collapse = screen.getByRole("button", { name: "Collapse all" });
    expect(expand).toBeDisabled();
    await user.click(collapse);
    expect(collapse).toBeDisabled();
    // the root's children stay: Extension, Guardrail, Provider and SqlPlugin, and the LLMClient itself.
    expect(screen.getAllByRole("article")).toHaveLength(5);
    await user.click(expand);
    expect(screen.getAllByRole("article")).toHaveLength(10);
  });

  it("reloads the tree, when it can", async () => {
    const user = userEvent.setup();
    const onReload = vi.fn();
    const { rerender } = render(<App architecture={leafArchitecture} onReload={onReload} />);
    await user.click(screen.getByRole("button", { name: "Reload" }));
    expect(onReload).toHaveBeenCalledOnce();
    rerender(<App architecture={leafArchitecture} />);
    expect(screen.queryByRole("button", { name: "Reload" })).not.toBeInTheDocument();
  });

  it("draws an LLMClient that uses nothing, without the expand and collapse buttons", () => {
    render(<App architecture={leafArchitecture} />);
    expect(screen.getByRole("status")).toHaveTextContent("1 resource · 0 levels deep");
    expect(screen.queryByRole("button", { name: "Collapse all" })).not.toBeInTheDocument();
  });

  it("draws a resource that the user can't read as a locked card", () => {
    render(<App architecture={lockedArchitecture} />);
    expect(screen.getByText("You can't read this resource")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("2 resources · 1 level deep");
  });

  it("suggests next steps for what the LLMClient is missing, and none when it has everything", () => {
    const { rerender } = render(<App architecture={leafArchitecture} />);
    expect(screen.getByRole("heading", { level: 2, name: "Make this LLMClient your own" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Add your first Guardrail" })).toBeInTheDocument();
    rerender(<App architecture={stackademyArchitecture} />);
    expect(screen.queryByRole("heading", { name: "Make this LLMClient your own" })).not.toBeInTheDocument();
  });
});

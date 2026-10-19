import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import Hero from "@/components/Hero";
import { authenticatedPage, notDeployedPage, publicPage, workbenchPage } from "@/mocks/fixtures";

describe("Hero", () => {
  it("shows a deployed LLMClient's url, and its card", () => {
    render(<Hero page={workbenchPage} />);
    expect(screen.getByRole("heading", { level: 1, name: "Deployed" })).toBeInTheDocument();
    expect(screen.getByText(`${workbenchPage.llmclient.url}/`)).toBeInTheDocument();
    expect(screen.getByText(/is live\. Its system prompt/)).toBeInTheDocument();
    for (const [label, value] of [
      ["Name", "stackademy"],
      ["Owner", "Ada Lovelace (admin)"],
      ["LLM provider", "openai"],
      ["Model", "gpt-6-luna"],
      ["Version", "1.0.0"],
      ["Access", "Public"],
    ]) {
      expect(screen.getByRole("row", { name: `${label} ${value}` })).toBeInTheDocument();
    }
    expect(screen.getByRole("link", { name: "Budgets" })).toBeInTheDocument();
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });

  it("tells how to deploy an LLMClient that isn't deployed", () => {
    render(<Hero page={notDeployedPage} />);
    expect(screen.getByRole("heading", { level: 1, name: "Not deployed yet" })).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "smarter cli" })).toHaveTextContent("smarter deploy llmclient stackademy");
    expect(screen.queryByRole("rowheader", { name: "Model" })).not.toBeInTheDocument();
  });

  it("says that an LLMClient with an api key requires one", () => {
    render(<Hero page={authenticatedPage} />);
    expect(screen.getByRole("row", { name: "Access Api key required" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Budgets" })).not.toBeInTheDocument();
  });

  it("shows the logo, and a way back to the workbench, on the public page", () => {
    render(<Hero page={publicPage} />);
    expect(screen.getByRole("img", { name: "The Smarter Project" })).toHaveAttribute("src", publicPage.links.logoUrl);
    expect(screen.getByRole("link", { name: "Back to the workbench" })).toBeInTheDocument();
    expect(screen.queryByRole("rowheader", { name: "Owner" })).not.toBeInTheDocument();
  });
});

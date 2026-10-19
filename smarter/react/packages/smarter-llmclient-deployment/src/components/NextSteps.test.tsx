import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import NextSteps from "@/components/NextSteps";
import { publicPage, sharedPage, workbenchPage } from "@/mocks/fixtures";

describe("NextSteps", () => {
  it("lists the integrations, and the origin that each needs allowed", () => {
    render(<NextSteps page={publicPage} />);
    for (const name of ["WordPress", "Drupal", "Shopify", "React, from npm", "Any web page, in html"]) {
      expect(screen.getByRole("heading", { name })).toBeInTheDocument();
    }
    expect(screen.getByRole("group", { name: "index.html" })).toHaveTextContent("data-chatbot");
    expect(screen.getByRole("group", { name: "manifest.yaml" })).toHaveTextContent("allowedOrigins");
    expect(screen.getByText('<smarter-chat chatbot="…"></smarter-chat>')).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "This LLMClient isn't yours" })).not.toBeInTheDocument();
  });

  it("has no clone guide for the LLMClient's owner", () => {
    render(<NextSteps page={workbenchPage} />);
    expect(screen.queryByRole("heading", { name: "This LLMClient isn't yours" })).not.toBeInTheDocument();
  });

  it("tells a user who may not change the LLMClient how to clone it", () => {
    render(<NextSteps page={sharedPage} />);
    expect(screen.getByRole("heading", { name: "This LLMClient isn't yours" })).toBeInTheDocument();
    expect(screen.getByText(/belongs to/)).toHaveTextContent("stackademy belongs to Ada Lovelace (admin)");
    expect(screen.getByRole("link", { name: "LLM Clients" })).toHaveAttribute("href", "/workbench/");
    expect(screen.getByRole("link", { name: "LLM Clients" })).toHaveAttribute("target", "_top");
    expect(screen.getByRole("link", { name: "How ownership of Smarter resources works" })).toHaveAttribute(
      "href",
      sharedPage.ownership!.ownershipDocsUrl,
    );
  });
});

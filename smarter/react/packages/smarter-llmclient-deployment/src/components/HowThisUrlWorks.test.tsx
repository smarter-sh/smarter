import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import HowThisUrlWorks from "@/components/HowThisUrlWorks";
import { authenticatedPage, notDeployedPage, workbenchPage } from "@/mocks/fixtures";

describe("HowThisUrlWorks", () => {
  it("shows the curl commands, the response, and the example prompts", () => {
    render(<HowThisUrlWorks page={workbenchPage} />);
    expect(screen.getAllByRole("group", { name: "bash" })[0]).toHaveTextContent("/config/");
    expect(screen.getAllByRole("group", { name: "bash" })[1]).toHaveTextContent("What courses are there?");
    expect(screen.getByRole("group", { name: /^200 OK\s+application\/json$/ })).toBeInTheDocument();
    expect(
      screen.getByText("Sends the LLMClient's first example prompt, and returns the LLM's response."),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Things to ask it" })).toBeInTheDocument();
    expect(screen.getByText("Is your program free?")).toBeInTheDocument();
    expect(screen.queryByText(/replace <YOUR-API-KEY> with yours/)).not.toBeInTheDocument();
  });

  it("without example prompts", () => {
    render(<HowThisUrlWorks page={notDeployedPage} />);
    expect(screen.getByText("Sends a prompt, and returns the LLM's response.")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Things to ask it" })).not.toBeInTheDocument();
  });

  it("tells how to send an api key", () => {
    render(<HowThisUrlWorks page={authenticatedPage} />);
    expect(screen.getByText(/replace <YOUR-API-KEY> with yours/)).toBeInTheDocument();
  });
});

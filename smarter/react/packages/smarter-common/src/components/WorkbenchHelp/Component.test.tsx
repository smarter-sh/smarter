import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import WorkbenchHelp from "./Component";

describe("WorkbenchHelp", () => {
  it("shows the help, and links to the documentation in a new tab", () => {
    render(<WorkbenchHelp title="Secrets" icon="ki-book-open" docsUrl="https://docs.example.com/" helpText="Help." />);
    expect(screen.getByRole("heading", { name: "Secrets" })).toBeInTheDocument();
    expect(screen.getByText("Help.")).toBeInTheDocument();
    const link = screen.getByRole("link", { name: /View documentation/ });
    expect(link).toHaveAttribute("href", "https://docs.example.com/");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
  });
});

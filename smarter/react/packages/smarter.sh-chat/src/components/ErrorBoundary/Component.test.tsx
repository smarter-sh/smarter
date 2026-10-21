import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import ErrorBoundary from "@/components/ErrorBoundary/Component";

function Broken(): never {
  throw new Error("It broke.");
}

describe("ErrorBoundary", () => {
  it("renders its children", () => {
    render(
      <ErrorBoundary>
        <p>Fine</p>
      </ErrorBoundary>,
    );
    expect(screen.getByText("Fine")).toBeInTheDocument();
  });

  it("displays a rendering error instead of its children", () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    render(
      <ErrorBoundary>
        <Broken />
      </ErrorBoundary>,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Something went wrong.It broke.");
  });
});

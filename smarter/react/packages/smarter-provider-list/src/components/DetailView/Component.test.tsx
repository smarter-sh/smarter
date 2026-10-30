import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { makeObject, sessionContext } from "@/mocks/fixtures";

import DetailView from "@/components/DetailView/Component";

describe("DetailView", () => {
  it("shows the provider's description, sections and metadata", () => {
    render(<DetailView sessionContext={sessionContext} object={makeObject(1)} onRequery={() => {}} />);
    expect(screen.getByText("An example, number 1.")).toBeInTheDocument();
    expect(screen.getByText("verified", { selector: ".badge" })).toBeInTheDocument();
    for (const title of ["Connectivity", "Status", "Publisher", "Terms of service", "Metadata"]) {
      expect(screen.getByRole("heading", { name: title })).toBeInTheDocument();
    }
    expect(screen.getByText("https://api.example.com/v1/")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /example_api_key/ })).toHaveAttribute("href", "/secret/secrets/hashed1/");
    expect(screen.getByText("example-model")).toBeInTheDocument();
    expect(screen.getByText("contact@example.com")).toBeInTheDocument();
    expect(screen.getAllByText("admin").length).toBeGreaterThan(0);
    expect(screen.getByText("example-1")).toBeInTheDocument();
    expect(screen.queryByText("Suspended", { selector: ".badge" })).not.toBeInTheDocument();
  });

  it("shows a suspended provider without an api key", () => {
    render(
      <DetailView
        sessionContext={sessionContext}
        object={makeObject(2, {
          isActive: false,
          isSuspended: true,
          isDeprecated: true,
          apiKey: null as never,
          tosAcceptedBy: null,
        })}
        onRequery={() => {}}
      />,
    );
    expect(screen.getByText("Inactive")).toBeInTheDocument();
    expect(screen.getByText("Suspended", { selector: ".badge" })).toBeInTheDocument();
    expect(screen.getByText("Deprecated", { selector: ".badge" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /example_api_key/ })).not.toBeInTheDocument();
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

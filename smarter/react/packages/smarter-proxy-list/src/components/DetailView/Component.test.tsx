import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { makeObject, sessionContext } from "@/mocks/fixtures";

import DetailView from "@/components/DetailView/Component";

describe("DetailView", () => {
  it("shows the Proxy's description, status, actions, sections and metadata", () => {
    render(<DetailView sessionContext={sessionContext} object={makeObject(1)} onRequery={() => {}} />);
    expect(screen.getByText("An example, number 1.")).toBeInTheDocument();
    expect(screen.getByText("Active")).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "Actions" })).toBeInTheDocument();
    for (const title of ["Endpoint", "Forwarding", "Authentication", "Metadata"]) {
      expect(screen.getByRole("heading", { name: title })).toBeInTheDocument();
    }
    expect(screen.getByText(`${window.location.origin}/api/v1/proxy/example-1/`)).toBeInTheDocument();
    expect(screen.getByText("https://api.openai.com/v1/")).toBeInTheDocument();
    expect(screen.getByText("60 seconds")).toBeInTheDocument();
    expect(screen.getAllByText("All paths").length).toBeGreaterThan(0);
    expect(screen.getByText("openai_api_key (provider's)")).toBeInTheDocument();
    expect(screen.getByText("Authorization: Bearer")).toBeInTheDocument();
    expect(screen.getByText("admin@example.com")).toBeInTheDocument();
  });

  it("shows a Proxy's own API key, headers and allowed paths", () => {
    render(
      <DetailView
        sessionContext={sessionContext}
        object={makeObject(2, {
          apiKeySecret: 7,
          apiKeySecretName: "anthropic_api_key",
          authHeader: "x-api-key",
          authScheme: "",
          headers: { "anthropic-version": "2023-06-01" },
          allowedPaths: ["/messages", "/models/*"],
        })}
        onRequery={() => {}}
      />,
    );
    expect(screen.getByText("anthropic_api_key")).toBeInTheDocument();
    expect(screen.getByText("x-api-key")).toBeInTheDocument();
    expect(screen.getByLabelText("JSON")).toHaveTextContent(/"anthropic-version": "2023-06-01"/);
    expect(screen.getByText("/messages")).toBeInTheDocument();
    expect(screen.getByText("/models/*")).toBeInTheDocument();
  });

  it("shows an inactive Proxy without an API key or a URL", () => {
    render(
      <DetailView
        sessionContext={sessionContext}
        object={makeObject(3, { isActive: false, apiKeySecretName: null, url: "" })}
        onRequery={() => {}}
      />,
    );
    expect(screen.getByText("Inactive")).toBeInTheDocument();
    expect(screen.getByText("None")).toBeInTheDocument();
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

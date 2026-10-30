import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { makeObject, sessionContext } from "@/mocks/fixtures";

import DetailView from "@/components/DetailView/Component";

describe("DetailView", () => {
  it("shows the MCPClient's description, sections and metadata", () => {
    render(<DetailView sessionContext={sessionContext} object={makeObject(1)} onRequery={() => {}} />);
    expect(screen.getByText("An example, number 1.")).toBeInTheDocument();
    expect(screen.getByText("Active")).toBeInTheDocument();
    expect(screen.getByText("Connected")).toBeInTheDocument();
    for (const title of ["Connection", "Authentication", "Capabilities", "MCP server", "Metadata"]) {
      expect(screen.getByRole("heading", { name: title })).toBeInTheDocument();
    }
    expect(screen.getByRole("link", { name: /https:\/\/mcp\.example\.com\/mcp/ })).toBeInTheDocument();
    expect(screen.getByText("example_mcp_api_key")).toBeInTheDocument();
    expect(screen.getByText("Authorization")).toBeInTheDocument();
    expect(screen.getByText("All tools")).toBeInTheDocument();
    expect(screen.getByText("search")).toBeInTheDocument();
    expect(screen.getByText("example-mcp-server")).toBeInTheDocument();
    expect(screen.queryByText("Last error")).not.toBeInTheDocument();
    expect(screen.getByText("admin@example.com")).toBeInTheDocument();
  });

  it("shows a failed MCPClient without authentication", () => {
    render(
      <DetailView
        sessionContext={sessionContext}
        object={makeObject(2, {
          isActive: false,
          status: "error",
          authType: "none",
          command: "npx example-server",
          headers: { "X-Client": "smarter" },
          allowedTools: ["search_*"],
          allowedResources: ["docs://*"],
          lastError: "Connection refused",
        })}
        onRequery={() => {}}
      />,
    );
    expect(screen.getByText("Inactive")).toBeInTheDocument();
    expect(screen.getByText("Connection error")).toBeInTheDocument();
    expect(screen.queryByText("example_mcp_api_key")).not.toBeInTheDocument();
    expect(screen.queryByText("API key header")).not.toBeInTheDocument();
    expect(screen.getByText("npx example-server")).toBeInTheDocument();
    expect(screen.getByText(/"X-Client": "smarter"/)).toBeInTheDocument();
    expect(screen.getByText("search_*")).toBeInTheDocument();
    expect(screen.getByText("docs://*")).toBeInTheDocument();
    expect(screen.getByText("Connection refused")).toBeInTheDocument();
  });

  it.each([
    ["disconnected", "Disconnected"],
    ["unconfigured", "Not yet connected"],
  ] as const)("shows the %s status", (status, label) => {
    render(<DetailView sessionContext={sessionContext} object={makeObject(3, { status })} onRequery={() => {}} />);
    expect(screen.getByText(label)).toBeInTheDocument();
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

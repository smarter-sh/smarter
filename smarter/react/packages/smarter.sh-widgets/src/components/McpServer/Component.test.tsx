import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import McpServer from "@/components/McpServer/Component";

describe("McpServer", () => {
  it("shows the command that adds this platform's MCP server to Claude Code", () => {
    render(<McpServer />);
    expect(screen.getByLabelText("Add this platform's MCP server to Claude Code")).toHaveTextContent(
      `claude mcp add --transport http smarter-project ${window.location.origin}/api/v1/mcp/smarter-project/`,
    );
  });

  it("links to the documentation", () => {
    render(<McpServer />);
    expect(screen.getByRole("link", { name: "Documentation" })).toHaveAttribute(
      "href",
      "https://docs.smarter.sh/en/latest/smarter-platform/smarter-project-mcp-server.html",
    );
  });

  it("shows another platform's MCP server", () => {
    render(<McpServer serverUrl="https://platform.smarter.sh/api/v1/mcp/smarter-project/" />);
    expect(screen.getByLabelText("Add this platform's MCP server to Claude Code")).toHaveTextContent(
      "claude mcp add --transport http smarter-project https://platform.smarter.sh/api/v1/mcp/smarter-project/",
    );
  });
});

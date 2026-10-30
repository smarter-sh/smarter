import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { makeObject, sessionContext } from "@/mocks/fixtures";

import DetailView from "@/components/DetailView/Component";

describe("DetailView", () => {
  it("shows the llmclient's description, status, actions, sections and metadata", () => {
    const llmclient = makeObject(1);
    render(<DetailView sessionContext={sessionContext} object={llmclient} onRequery={() => {}} />);
    expect(screen.getByText(llmclient.description)).toBeInTheDocument();
    expect(screen.getByText("Not deployed")).toBeInTheDocument();
    expect(screen.getByText("Ready")).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "Actions" })).toBeInTheDocument();
    for (const title of [
      "Model",
      "Tools",
      "Chat app",
      "Authentication",
      "Cross-origin access (CORS)",
      "Endpoints",
      "Hosting",
      "Metadata",
    ]) {
      expect(screen.getByRole("heading", { name: title })).toBeInTheDocument();
    }
    expect(screen.getByText("gpt-6-luna")).toBeInTheDocument();
    expect(screen.getByText("You are a helpful llmclient.")).toBeInTheDocument();
    // the tools are chips, not a comma-separated list.
    for (const name of [
      "get_current_weather()",
      "example_configuration",
      "everlasting_gobstopper",
      "example_mcpclient",
      "example_guardrail",
    ]) {
      expect(screen.getByText(name).tagName).toBe("LI");
    }
    expect(screen.getByText("What is an Everlasting Gobstopper?")).toBeInTheDocument();
    expect(screen.getByLabelText("CSS")).toHaveTextContent(/app-logo-url: url\(/);
    expect(screen.getByText("https://example.com")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: llmclient.urlChatapp })).toHaveAttribute("href", llmclient.urlChatapp);
    expect(screen.getByText("Not Verified")).toBeInTheDocument();
    expect(screen.getByText("example-1")).toBeInTheDocument();
    expect(screen.getByText("admin@example.com")).toBeInTheDocument();
  });

  it("shows a deployed llmclient's custom domains and api keys' ids", () => {
    render(
      <DetailView
        sessionContext={sessionContext}
        object={makeObject(2, {
          deployed: true,
          ready: false,
          isAuthenticationRequired: true,
          apiKeys: [{ id: 1, apiKey: "00000000-0000-0000-0000-000000000001" }],
          customDomains: [{ domainName: "example.com", verificationStatus: "verified" }, { domainName: "example.org" }],
        })}
        onRequery={() => {}}
      />,
    );
    expect(screen.getByText("Deployed")).toBeInTheDocument();
    expect(screen.getByText("Not ready")).toBeInTheDocument();
    expect(screen.getByText("00000000-0000-0000-0000-000000000001")).toBeInTheDocument();
    expect(screen.getByText("example.com (verified)")).toBeInTheDocument();
    expect(screen.getByText("example.org")).toBeInTheDocument();
  });

  it("shows an llmclient without tools or styles", () => {
    render(
      <DetailView
        sessionContext={sessionContext}
        object={makeObject(3, {
          functions: undefined as never,
          plugins: undefined as never,
          mcpclients: [],
          guardrails: [],
          customDomains: undefined as never,
          apiKeys: undefined as never,
          styles: null,
        })}
        onRequery={() => {}}
      />,
    );
    for (const name of ["get_current_weather()", "example_configuration", "example_mcpclient", "example_guardrail"]) {
      expect(screen.queryByText(name)).not.toBeInTheDocument();
    }
    expect(screen.queryByText(/"appLogoUrl"/)).not.toBeInTheDocument();
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
    await userEvent.setup().click(screen.getByRole("button", { name: "gibberish" }));
    expect(onTag).toHaveBeenCalledWith("gibberish");
  });
});

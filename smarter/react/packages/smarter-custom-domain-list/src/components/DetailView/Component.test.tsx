import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { makeObject, sessionContext } from "@/mocks/fixtures";

import DetailView from "@/components/DetailView/Component";

const LLMCLIENT = {
  id: 1,
  name: "stackademy",
  deployed: true,
  url: "https://stackademy.chat.example.com/",
  sandboxUrl: "/workbench/llm-clients/hashed1/",
  manifestUrl: "/workbench/llm-clients/hashed1/manifest/",
  owner: "admin",
};

describe("DetailView", () => {
  it("shows the domain's description, sections, DNS records and metadata", () => {
    render(<DetailView sessionContext={sessionContext} object={makeObject(1)} onRequery={() => {}} />);
    expect(screen.getByText("An example, number 1.")).toBeInTheDocument();
    expect(screen.getAllByText("Verified").length).toBeGreaterThan(0);
    for (const title of ["Domain", "LLMClient", "DNS records", "Metadata"]) {
      expect(screen.getByRole("heading", { name: title })).toBeInTheDocument();
    }
    expect(screen.getAllByText("example-1.example.com").length).toBe(2);
    expect(screen.getByText("Z00000000000001")).toBeInTheDocument();
    expect(screen.getByText("NS")).toBeInTheDocument();
    expect(screen.getByText("ns-1.awsdns-01.com.")).toBeInTheDocument();
    expect(screen.getByText("No LLMClient uses this domain")).toBeInTheDocument();
    expect(screen.getByText("admin@example.com")).toBeInTheDocument();
  });

  it("shows the LLMClient that the domain serves", () => {
    render(
      <DetailView
        sessionContext={sessionContext}
        object={makeObject(2, { llmclient: LLMCLIENT })}
        onRequery={() => {}}
      />,
    );
    expect(screen.getByRole("link", { name: "stackademy" })).toHaveAttribute(
      "href",
      "/workbench/llm-clients/hashed1/manifest/",
    );
    expect(screen.getByText("https://stackademy.chat.example.com/")).toBeInTheDocument();
    expect(screen.queryByText("No LLMClient uses this domain")).not.toBeInTheDocument();
  });

  it("shows why a domain's verification failed, without DNS records", () => {
    render(
      <DetailView
        sessionContext={sessionContext}
        object={makeObject(3, {
          verificationStatus: "Failed",
          verifiedAt: null,
          verificationMessage: "The NS records are wrong.",
          dnsRecords: [],
        })}
        onRequery={() => {}}
      />,
    );
    expect(screen.getAllByText("Failed").length).toBeGreaterThan(0);
    expect(screen.getByText("The NS records are wrong.")).toBeInTheDocument();
    expect(screen.queryByRole("columnheader", { name: "TTL" })).not.toBeInTheDocument();
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

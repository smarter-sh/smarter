import { render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { makeObject, sessionContext } from "@/mocks/fixtures";
import type { LLMClient } from "@/lib/Types";

import { CardView } from "@/components/CardView/Component";

/** The value of a card's detail row, by its label. */
function detail(label: string) {
  const row = screen
    .getAllByRole("row")
    .find((r) => within(r).queryAllByRole("cell")[0]?.textContent?.startsWith(label));
  return within(row!).getAllByRole("cell")[1];
}

describe("CardView", () => {
  beforeEach(() => {
    vi.spyOn(console, "debug").mockImplementation(() => {});
  });

  it("shows an LLMClient's details", () => {
    render(<CardView sessionContext={sessionContext} objects={[makeObject(1)]} onRequery={() => {}} />);
    expect(screen.getByRole("link", { name: "example_1" })).toBeInTheDocument();
    expect(detail("Status")).toHaveTextContent("Not deployed");
    expect(detail("Functions")).toHaveTextContent("get_current_weather()");
    expect(detail("Plugins")).toHaveTextContent("example_configuration, everlasting_gobstopper");
    expect(detail("Custom Domains")).toHaveTextContent("No value");
    expect(detail("API Keys")).toHaveTextContent("No value");
  });

  it("shows a deployed LLMClient's domains and API keys", () => {
    const llmclient = makeObject(1, {
      deployed: true,
      customDomains: [{ id: 1, name: "example.com" }],
      apiKeys: [{ id: 2, name: "key" }],
    } as Partial<LLMClient>);
    render(<CardView sessionContext={sessionContext} objects={[llmclient]} onRequery={() => {}} />);
    expect(detail("Status")).toHaveTextContent("Deployed");
    expect(detail("Custom Domains")).toHaveTextContent("example.com");
    expect(detail("API Keys")).toHaveTextContent('"name":"key"');
  });

  it("shows an LLMClient without functions, plugins or owner", () => {
    const llmclient = makeObject(1, {
      functions: undefined,
      plugins: [{ id: 1, name: "" }],
      customDomains: undefined,
      apiKeys: undefined,
      userProfile: undefined,
    } as unknown as Partial<LLMClient>);
    render(<CardView sessionContext={sessionContext} objects={[llmclient]} onRequery={() => {}} />);
    expect(detail("Functions")).toHaveTextContent("No value");
    expect(detail("Plugins")).toHaveTextContent("No value");
    expect(detail("Owner")).toHaveTextContent("No value");
  });

  it("shows nothing without a list of objects", () => {
    render(<CardView sessionContext={sessionContext} objects={null as unknown as LLMClient[]} onRequery={() => {}} />);
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });
});

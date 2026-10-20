import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import GettingStarted from "@/components/GettingStarted";
import { DOCS_URLS } from "@/lib/const";
import { consoleLinks, leafTree, lockedTree, stackademyTree } from "@/mocks/fixtures";

const section = (name: string) => screen.getByRole("region", { name });

describe("GettingStarted", () => {
  it("suggests a Guardrail, tools, styles and an api key for an unstyled LLMClient that uses nothing", () => {
    render(<GettingStarted tree={leafTree} styled={false} links={consoleLinks} />);
    expect(screen.getByRole("heading", { level: 2, name: "Make this LLMClient your own" })).toBeInTheDocument();
    expect(section("Add your first Guardrail")).toBeInTheDocument();
    expect(section("Add your first tool")).toBeInTheDocument();
    expect(section("Style its chat")).toBeInTheDocument();
    expect(section("Add an api key")).toBeInTheDocument();
  });

  it("explains Guardrails, links to the Guardrails page and the docs, and opens the manifest", () => {
    render(<GettingStarted tree={leafTree} styled={false} links={consoleLinks} />);
    const guardrail = within(section("Add your first Guardrail"));
    expect(guardrail.getByText(/A Guardrail screens the text/)).toBeInTheDocument();
    expect(guardrail.getByRole("link", { name: "Browse the Guardrails" })).toHaveAttribute("href", "/guardrail/");
    expect(guardrail.getByRole("link", { name: "Built-in Guardrails" })).toHaveAttribute(
      "href",
      DOCS_URLS.builtInGuardrails,
    );
    expect(guardrail.getByRole("link", { name: "Guardrails" })).toHaveAttribute("href", DOCS_URLS.guardrails);
    expect(guardrail.getByRole("link", { name: "Open this LLMClient's manifest" })).toHaveAttribute(
      "href",
      leafTree.url,
    );
    expect(guardrail.getByRole("group", { name: "Two built-in Guardrails" })).toHaveTextContent(
      "prompt_injection_keyword_input",
    );
  });

  it("compares plugins, Extensions and MCPClients, each with an example and its pages", () => {
    render(<GettingStarted tree={leafTree} styled={false} links={consoleLinks} />);
    const tools = within(section("Add your first tool"));
    for (const [name, example, browse, url, docs] of [
      ["Plugins", "everlasting_gobstopper", "Browse the plugins", "/llm-tools/", DOCS_URLS.plugins],
      ["Extensions", "calculator", "Browse the Extensions", "/extensions/", DOCS_URLS.extensions],
      ["MCPClients", "deepwiki", "Browse the MCPClients", "/mcpclient/", DOCS_URLS.mcpClients],
    ]) {
      expect(tools.getByRole("heading", { level: 4, name })).toBeInTheDocument();
      expect(tools.getByRole("group", { name })).toHaveTextContent(example);
      expect(tools.getByRole("link", { name: browse })).toHaveAttribute("href", url);
      expect(tools.getByRole("link", { name })).toHaveAttribute("href", docs);
    }
    expect(tools.getByRole("link", { name: "Plugins, Extensions and MCP servers compared" })).toHaveAttribute(
      "href",
      DOCS_URLS.toolsCompared,
    );
    expect(tools.getByRole("link", { name: "Extensibility" })).toHaveAttribute("href", DOCS_URLS.extensibility);
  });

  it("explains styles, with an example and the docs", () => {
    render(<GettingStarted tree={leafTree} styled={false} links={consoleLinks} />);
    const styles = within(section("Style its chat"));
    expect(styles.getByRole("group", { name: "The chat's styles" })).toHaveTextContent("conversationHeader:");
    expect(styles.getByRole("link", { name: "Styling your LLMClient's chat" })).toHaveAttribute(
      "href",
      DOCS_URLS.styles,
    );
  });

  it("explains api keys, with an example, the API Keys page and the docs", () => {
    render(<GettingStarted tree={leafTree} styled={false} links={consoleLinks} />);
    const apiKey = within(section("Add an api key"));
    expect(apiKey.getByText(/this LLMClient is public once it is deployed/)).toBeInTheDocument();
    expect(apiKey.getByText(/Deployment tab/)).toBeInTheDocument();
    expect(apiKey.getByRole("group", { name: "The LLMClient's api key" })).toHaveTextContent("apiKey: my_api_key");
    expect(apiKey.getByRole("link", { name: "Browse your api keys" })).toHaveAttribute("href", "/authtoken/");
    expect(apiKey.getByRole("link", { name: "API Keys" })).toHaveAttribute("href", DOCS_URLS.apiKeys);
    expect(apiKey.getByRole("link", { name: "Open this LLMClient's manifest" })).toHaveAttribute("href", leafTree.url);
  });

  it("suggests only what is missing", () => {
    render(<GettingStarted tree={lockedTree} styled={true} links={consoleLinks} />);
    expect(screen.queryByRole("region", { name: "Add your first Guardrail" })).not.toBeInTheDocument();
    expect(section("Add your first tool")).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Style its chat" })).not.toBeInTheDocument();
    expect(section("Add an api key")).toBeInTheDocument();
  });

  it("doesn't suggest an api key for an LLMClient that has one", () => {
    const apiKey = stackademyTree.children.find((child) => child.kind === "SmarterAuthToken")!;
    render(<GettingStarted tree={{ ...leafTree, children: [apiKey] }} styled={false} links={consoleLinks} />);
    expect(screen.queryByRole("region", { name: "Add an api key" })).not.toBeInTheDocument();
    expect(section("Add your first Guardrail")).toBeInTheDocument();
  });

  it("suggests nothing for an LLMClient that has everything", () => {
    const { container } = render(<GettingStarted tree={stackademyTree} styled={true} links={consoleLinks} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("names the manifest without a link, when the LLMClient has no manifest page", () => {
    render(<GettingStarted tree={{ ...leafTree, url: null }} styled={true} links={consoleLinks} />);
    expect(screen.queryByRole("link", { name: "Open this LLMClient's manifest" })).not.toBeInTheDocument();
    expect(screen.getAllByText(/Open this LLMClient's manifest/).length).toBeGreaterThan(0);
  });
});

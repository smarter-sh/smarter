import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { makeProvider, providers, sparseProvider, suspendedProvider } from "@/mocks/fixtures";

import LLMProviderMetaData from "@/components/LLMProviderMetaData/Component";

const section = (name: string) => screen.getByRole("region", { name });
const detail = (region: HTMLElement, label: string) => within(region).getByRole("definition", { name: label });

describe("LLMProviderMetaData", () => {
  it("renders nothing without a provider", () => {
    const { container } = render(<LLMProviderMetaData provider={null} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("identifies the provider, and links to its page and its own sites", () => {
    render(<LLMProviderMetaData provider={providers[0]} />);

    expect(screen.getByRole("heading", { name: "openai" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "openai" })).toHaveAttribute("href", "/provider/providers/rMTAwMDAwNwx/");
    expect(screen.getByRole("img", { name: "openai logo" })).toBeInTheDocument();
    expect(screen.getByText("v1.0.0")).toBeInTheDocument();
    expect(screen.getByText("OpenAI provides advanced AI models and APIs.")).toBeInTheDocument();

    const links = within(screen.getByRole("navigation", { name: "Provider links" }));
    expect(links.getByRole("link", { name: "Website" })).toHaveAttribute("href", "https://openai.example.com");
    expect(links.getByRole("link", { name: "Docs" })).toHaveAttribute("href", "https://docs.openai.example.com");
    expect(links.getByRole("link", { name: "Terms" })).toHaveAttribute("href", "https://openai.example.com/terms/");
    expect(links.getByRole("link", { name: "Privacy" })).toHaveAttribute("target", "_blank");
  });

  it("shows every flag, and whether it's set", () => {
    render(<LLMProviderMetaData provider={suspendedProvider} />);

    const flags = within(screen.getByRole("list", { name: "Flags" }));
    expect(flags.getAllByRole("listitem")).toHaveLength(8);
    expect(flags.getByText("Verified: yes")).toBeInTheDocument();
    expect(flags.getByText("Active: no")).toBeInTheDocument();
    expect(flags.getByTitle("Suspended: yes")).toHaveClass("provider-meta-flag-warning");
    expect(flags.getByTitle("Official: yes")).toHaveClass("provider-meta-flag-on");
    expect(flags.getByTitle("Deprecated: no")).toHaveClass("provider-meta-flag-off");
  });

  it("labels the status, and shows a status that it doesn't know as it is", () => {
    const { rerender } = render(<LLMProviderMetaData provider={suspendedProvider} />);
    // the status badge comes before the flags, whose own "Suspended" chip is the second.
    expect(screen.getAllByText("Suspended")[0]).toHaveClass("badge-light-danger");

    rerender(<LLMProviderMetaData provider={makeProvider(5, "newai", { status: "pending" })} />);
    expect(screen.getByText("pending")).toHaveClass("badge-light-secondary");
  });

  it("groups the provider's details", () => {
    render(<LLMProviderMetaData provider={providers[0]} />);

    const connection = section("Connection");
    expect(detail(connection, "Slug")).toHaveTextContent("openai");
    expect(detail(connection, "Base URL")).toHaveTextContent("https://api.openai.example.com/v1/");
    expect(detail(connection, "Default model")).toHaveTextContent("gpt-4o-mini");
    expect(detail(connection, "Connectivity path")).toHaveTextContent("chat/completions");
    expect(within(connection).getByRole("link", { name: "openai_api_key" })).toHaveAttribute(
      "href",
      "/secret/secrets/rMTAwMDAxMQx/",
    );

    const ownership = section("Ownership");
    expect(detail(ownership, "Account")).toHaveTextContent("3141-5926-5359");
    expect(detail(ownership, "Owner")).toHaveTextContent("adminadmin@example.com");
    expect(detail(ownership, "Ownership requested")).toHaveTextContent("None");
    expect(detail(ownership, "Created")).toHaveTextContent("Jun 1, 2026");
    expect(within(detail(ownership, "Updated")).getByText("Jun 15, 2026")).toHaveAttribute(
      "title",
      expect.stringContaining("Jun 15, 2026"),
    );

    const terms = section("Terms of service");
    expect(detail(terms, "Accepted")).toHaveTextContent("Yes");
    expect(within(detail(terms, "Accepted by")).getByRole("link")).toHaveAttribute("href", "mailto:admin@example.com");
    expect(detail(terms, "Accepted on")).toHaveTextContent("Jun 1, 2026");

    const contact = section("Contact");
    expect(detail(contact, "Contact email")).toHaveTextContent("contact@openai.example.comVerified Jun 1, 2026");
    expect(detail(contact, "Support email")).toHaveTextContent("support@openai.example.comVerified Jun 1, 2026");
  });

  it("shows tags, and each annotation as key: value", () => {
    render(<LLMProviderMetaData provider={providers[0]} />);

    const tags = within(screen.getByRole("list", { name: "Tags" }));
    expect(tags.getAllByRole("listitem").map((li) => li.textContent)).toEqual(["llm", "chat"]);
    const annotations = within(screen.getByRole("list", { name: "Annotations" }));
    expect(annotations.getAllByRole("listitem").map((li) => li.textContent)).toEqual([
      "smarter.sh/purpose: testing",
      "smarter.sh/tier: 2",
    ]);
  });

  it("says what a sparse provider doesn't have, rather than leave gaps", () => {
    render(<LLMProviderMetaData provider={sparseProvider} />);

    expect(screen.queryByRole("img")).not.toBeInTheDocument();
    expect(screen.getByText("L")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "localllm" })).not.toBeInTheDocument();
    expect(screen.getByText("Unverified")).toBeInTheDocument();
    expect(screen.queryByRole("navigation", { name: "Provider links" })).not.toBeInTheDocument();

    const connection = section("Connection");
    expect(detail(connection, "Default model")).toHaveTextContent("None");
    expect(detail(connection, "Connectivity path")).toHaveTextContent("None");
    expect(detail(connection, "API key secret")).toHaveTextContent("None");

    const terms = section("Terms of service");
    expect(detail(terms, "Accepted")).toHaveTextContent("No");
    expect(detail(terms, "Accepted by")).toHaveTextContent("None");
    expect(detail(terms, "Accepted on")).toHaveTextContent("None");

    const contact = section("Contact");
    expect(detail(contact, "Contact email")).toHaveTextContent("None");
    expect(detail(contact, "Support email")).toHaveTextContent("None");

    expect(screen.queryByRole("list", { name: "Tags" })).not.toBeInTheDocument();
    expect(screen.queryByRole("list", { name: "Annotations" })).not.toBeInTheDocument();
  });

  it("shows an unverified email, a requested ownership, and an API key without a page", () => {
    render(<LLMProviderMetaData provider={suspendedProvider} />);

    expect(detail(section("Contact"), "Contact email")).toHaveTextContent("contact@shadyai.example.comNot verified");
    expect(within(detail(section("Ownership"), "Ownership requested")).getByRole("link")).toHaveAttribute(
      "href",
      "mailto:claims@shadyai.example.com",
    );
    expect(detail(section("Connection"), "API key secret")).toHaveTextContent("shadyai_api_key");
    expect(within(section("Connection")).queryByRole("link")).not.toBeInTheDocument();
  });

  it("shows an annotation whose value isn't a string as JSON, and an invalid date as none", () => {
    render(
      <LLMProviderMetaData
        provider={makeProvider(6, "oddai", { annotations: [{ list: [1, 2] }], updatedAt: "not a date" })}
      />,
    );
    expect(screen.getByText("list: [1,2]")).toBeInTheDocument();
    expect(detail(section("Ownership"), "Updated")).toHaveTextContent("None");
  });
});

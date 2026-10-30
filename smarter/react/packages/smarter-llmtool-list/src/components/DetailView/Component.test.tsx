import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { makeObject, sessionContext } from "@/mocks/fixtures";

import DetailView from "@/components/DetailView/Component";

describe("DetailView", () => {
  it("shows the plugin's description, sections and metadata", () => {
    render(<DetailView sessionContext={sessionContext} object={makeObject(1)} onRequery={() => {}} />);
    expect(screen.getByText("An example, number 1.")).toBeInTheDocument();
    expect(screen.getByText("Ready")).toBeInTheDocument();
    for (const title of ["Plugin", "Selector", "Prompt", "Static data", "Metadata"]) {
      expect(screen.getByRole("heading", { name: title })).toBeInTheDocument();
    }
    expect(screen.getByText("search_terms")).toBeInTheDocument();
    expect(screen.getByText("gobstopper")).toBeInTheDocument();
    expect(screen.getByText("gpt-4o-mini")).toBeInTheDocument();
    expect(screen.getByText("You are a helpful assistant.")).toBeInTheDocument();
    expect(screen.getByText(/An example static plugin\./)).toBeInTheDocument();
    expect(screen.getByText("admin@example.com")).toBeInTheDocument();
  });

  it("shows a SQL plugin's query", () => {
    render(
      <DetailView
        sessionContext={sessionContext}
        object={makeObject(2, {
          ready: false,
          pluginClass: "sql",
          staticData: null,
          sqlData: {
            connection: "example_sql_connection",
            description: "Looks up courses.",
            parameters: { type: "object", required: [], properties: {}, additionalProperties: false },
            sqlQuery: "SELECT 1",
            testValues: [],
            limit: 10,
          },
        })}
        onRequery={() => {}}
      />,
    );
    expect(screen.getByText("Not ready")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "SQL query" })).toBeInTheDocument();
    expect(screen.getByText("example_sql_connection")).toBeInTheDocument();
    expect(screen.getByLabelText("SQL")).toHaveTextContent("SELECT 1");
    expect(screen.getAllByLabelText("JSON")[0]).toHaveTextContent(/"additionalProperties": false/);
  });

  it("shows an API plugin's request", () => {
    render(
      <DetailView
        sessionContext={sessionContext}
        object={makeObject(3, {
          pluginClass: "api",
          staticData: null,
          apiData: { connection: "example_api_connection", method: "GET", endpoint: "/forecast/", urlParams: [] },
        })}
        onRequery={() => {}}
      />,
    );
    expect(screen.getByRole("heading", { name: "API request" })).toBeInTheDocument();
    expect(screen.getByText("example_api_connection")).toBeInTheDocument();
    expect(screen.getByText("/forecast/")).toBeInTheDocument();
    expect(screen.getByText("urlParams")).toBeInTheDocument();
  });

  it("shows a plugin without a selector, prompt or data", () => {
    render(
      <DetailView
        sessionContext={sessionContext}
        object={makeObject(4, { selector: null as never, prompt: null as never, staticData: null })}
        onRequery={() => {}}
      />,
    );
    expect(screen.getByRole("heading", { name: "Data" })).toBeInTheDocument();
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

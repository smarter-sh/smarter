import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  DetailField,
  DetailOverview,
  DetailSection,
  DetailValue,
  asYaml,
  prettyJson,
  ResourceMetadataSection,
  styleObjectAsCss,
} from "./DetailFields";

describe("DetailValue", () => {
  it("shows a missing value as a dash", () => {
    for (const value of [null, undefined, "", []]) {
      const { unmount } = render(<DetailValue value={value} />);
      expect(screen.getByTitle("No value")).toHaveTextContent("—");
      unmount();
    }
  });

  it("formats each type", () => {
    render(
      <dl>
        <DetailValue value={true} type="bool" />
        <DetailValue value={false} type="bool" />
        <DetailValue value={null} type="bool" />
        <DetailValue value={1234} type="number" />
        <DetailValue value="https://example.com/a" type="url" />
        <DetailValue value="abc" type="code" />
        <DetailValue value={{ a: 1 }} type="json" />
        <DetailValue value='{"b":2}' type="json" />
        <DetailValue value="not json" type="json" />
        <DetailValue value={["x", "y"]} type="list" />
        <DetailValue value="z" type="list" />
        <DetailValue value="2026-06-01T12:00:00Z" type="dateTime" />
        <DetailValue value={{ c: 3 }} />
        <DetailValue value={7} />
      </dl>,
    );
    expect(screen.getByText("Yes")).toBeInTheDocument();
    expect(screen.getByText("No")).toBeInTheDocument();
    expect(screen.getByText("1,234")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "https://example.com/a" })).toHaveAttribute("target", "_blank");
    expect(screen.getByText("abc").tagName).toBe("CODE");
    expect(screen.getByText(/"a": 1/)).toBeInTheDocument();
    expect(screen.getByText(/"b": 2/)).toBeInTheDocument();
    expect(screen.getByText("not json")).toBeInTheDocument();
    expect(screen.getByText("x")).toBeInTheDocument();
    expect(screen.getByText("z")).toBeInTheDocument();
    expect(screen.getByText(/ago$/)).toBeInTheDocument();
    expect(screen.getByText('{"c":3}')).toBeInTheDocument();
    expect(screen.getByText("7")).toBeInTheDocument();
  });
});

describe("DetailSection, DetailField and DetailOverview", () => {
  it("show a titled section of labeled fields, with help", () => {
    render(
      <>
        <DetailOverview description="What it is.">
          <span>aside</span>
        </DetailOverview>
        <DetailSection title="Detection" icon="scan-barcode">
          <DetailField label="Strategy" value="regex" help="How it detects." />
          <DetailField label="Chips" wide>
            <span>custom</span>
          </DetailField>
        </DetailSection>
      </>,
    );
    expect(screen.getByText("What it is.")).toBeInTheDocument();
    expect(screen.getByText("aside")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Detection" })).toBeInTheDocument();
    expect(screen.getAllByRole("term").map((term) => term.textContent)).toEqual(["StrategyHow it detects.", "Chips"]);
    expect(screen.getByTitle("How it detects.")).toBeInTheDocument();
    expect(screen.getByText("custom")).toBeInTheDocument();
  });

  it("says when there is no description", () => {
    render(<DetailOverview description="" />);
    expect(screen.getByText("No description.")).toBeInTheDocument();
  });
});

describe("ResourceMetadataSection", () => {
  it("shows the fields that every resource has", () => {
    render(
      <ResourceMetadataSection
        resource={{
          id: 3,
          hashedId: "rMwx",
          version: "1.0.0",
          createdAt: "2026-06-01T12:00:00Z",
          updatedAt: "2026-06-02T12:00:00Z",
          tags: ["red"],
          annotations: { "example.com/team": "a" },
          userProfile: { user: { username: "ada", email: "ada@example.com" }, account: { accountNumber: "1-2-3" } },
        }}
      >
        <DetailField label="Extra" value="more" />
      </ResourceMetadataSection>,
    );
    for (const text of ["ada", "ada@example.com", "1-2-3", "1.0.0", "rMwx", "red", "example.com/team: a", "more"]) {
      expect(screen.getByText(text)).toBeInTheDocument();
    }
  });
});

describe("styleObjectAsCss", () => {
  it("writes a style object as CSS, as Prettier formats it", () => {
    expect(
      styleObjectAsCss({
        appLogoUrl: "https://example.com/logo.png",
        googleFont: "Inter",
        borderRadius: "8px",
        empty: "",
        conversationHeader: { backgroundColor: "#231f20", color: "#ffffff" },
        messageList: { backgroundColor: "rgba(255, 255, 255, 0.88)", bubble: { padding: 4 } },
      }),
    ).toBe(
      [
        ":root {",
        '  app-logo-url: url("https://example.com/logo.png");',
        '  google-font: "Inter";',
        "  border-radius: 8px;",
        "}",
        "",
        ".conversation-header {",
        "  background-color: #231f20;",
        "  color: #ffffff;",
        "}",
        "",
        ".message-list {",
        "  background-color: rgba(255, 255, 255, 0.88);",
        "",
        "  .bubble {",
        "    padding: 4;",
        "  }",
        "}",
        "",
      ].join("\n"),
    );
  });

  it("is the css type of DetailValue, from an object or JSON, and shows anything else as it is", () => {
    render(
      <>
        <DetailValue value={{ color: "red" }} type="css" />
        <DetailValue value='{"font": "x"}' type="css" />
        <DetailValue value="not json" type="css" />
        <DetailValue value={[1]} type="css" />
      </>,
    );
    expect(screen.getByText(/color: red;/)).toBeInTheDocument();
    expect(screen.getByText(/font: "x";/)).toBeInTheDocument();
    expect(screen.getByText("not json")).toBeInTheDocument();
    expect(screen.getByText("[1]")).toBeInTheDocument();
  });
});

describe("prettyJson", () => {
  it("keeps what fits on one line, and breaks what doesn't, as Prettier does", () => {
    const testValues = [
      { name: "description", value: "AI" },
      { name: "max_cost", value: "500" },
    ];
    expect(prettyJson(testValues)).toBe(
      ["[", '  { "name": "description", "value": "AI" },', '  { "name": "max_cost", "value": "500" }', "]"].join("\n"),
    );
    expect(prettyJson({ a: [], b: {}, c: null, d: [1, 2] })).toBe('{ "a": [], "b": {}, "c": null, "d": [1, 2] }');
    expect(prettyJson({ text: "x".repeat(80) })).toBe(`{\n  "text": "${"x".repeat(80)}"\n}`);
  });
});

describe("asYaml", () => {
  it("writes data, or a JSON string, as YAML, a text of several lines as a block, and leaves other strings", () => {
    expect(asYaml({ about: "line one\nline two\n", links: [{ docs: "https://example.com" }] })).toBe(
      "about: |\n  line one\n  line two\nlinks:\n  - docs: https://example.com\n",
    );
    expect(asYaml('{"a": 1}')).toBe("a: 1\n");
    expect(asYaml("not json")).toBe("not json");
  });
});

/**
 * Test a list package's CardView renderDetailRow(), which every resource list page copies.
 *
 * Each package calls it from src/components/CardView/renderDetail.test.tsx:
 *
 *     import { testRenderDetailRow } from "@test/renderDetail";
 *     import { renderDetailRow } from "./renderDetail";
 *     testRenderDetailRow(renderDetailRow);
 */
import type { ReactNode } from "react";
import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

type DataType = "string" | "url" | "dateTime" | "number" | "bool" | "json" | "str[]" | null;
type RenderDetailRow = (label: string, value: unknown, dataType?: DataType, microHelp?: string | null) => ReactNode;

export function testRenderDetailRow(renderDetailRow: RenderDetailRow) {
  /** Render one detail row, and return its value cell. */
  function valueCell(value: unknown, dataType?: DataType, microHelp?: string | null) {
    render(
      <table>
        <tbody>{renderDetailRow("Label", value, dataType, microHelp)}</tbody>
      </table>,
    );
    return screen.getAllByRole("cell")[1];
  }

  describe("renderDetailRow", () => {
    it.each([null, undefined, ""])("shows 'No value' for %j", (value) => {
      expect(valueCell(value, "string")).toHaveTextContent("No value");
    });

    it("marks the label with its micro help", () => {
      valueCell("x", "string", "Help text");
      expect(screen.getByTitle("Help text")).toHaveTextContent("(*)");
    });

    it("shows a string as it is", () => {
      expect(valueCell("plain")).toHaveTextContent("plain");
    });

    it("shows a number with no data type", () => {
      expect(valueCell(7)).toHaveTextContent("7");
    });

    it("shows a boolean with no data type", () => {
      expect(valueCell(true, "string")).toBeInTheDocument();
    });

    it("shows an object as JSON when it has no data type", () => {
      expect(valueCell({ a: 1 }, null)).toHaveTextContent('{"a":1}');
    });

    it("stringifies other values", () => {
      expect(valueCell(Symbol("s"), "string")).toHaveTextContent("Symbol(s)");
    });

    it("formats a dateTime", () => {
      expect(valueCell("2024-05-24T12:00:00Z", "dateTime")).toHaveTextContent("2024");
    });

    it("shows nothing for a dateTime that isn't a string or number", () => {
      expect(valueCell({ when: 1 }, "dateTime")).toBeEmptyDOMElement();
    });

    it("links a url", () => {
      const link = within(valueCell("https://example.com", "url")).getByRole("link");
      expect(link).toHaveAttribute("href", "https://example.com");
      expect(link).toHaveTextContent("https://example.com");
    });

    it("links an object url with its JSON as the text", () => {
      expect(within(valueCell({ u: 1 }, "url")).getByRole("link")).toHaveTextContent('{"u":1}');
    });

    it("links a url with no text when it is neither a string, number nor object", () => {
      expect(within(valueCell(true, "url")).getByRole("link")).toBeEmptyDOMElement();
    });

    it("shows a number", () => {
      expect(valueCell("42", "number")).toHaveTextContent("42");
    });

    it.each([
      [true, "Yes"],
      [false, "No"],
    ])("shows the bool %s as %s", (value, text) => {
      expect(valueCell(value, "bool")).toHaveTextContent(text);
    });

    it("pretty-prints a JSON object", () => {
      // indented JSON, whose whitespace toHaveTextContent collapses.
      expect(valueCell({ a: 1 }, "json")).toHaveTextContent('{ "a": 1 }');
    });

    it("pretty-prints a JSON string", () => {
      expect(valueCell('{"a":1}', "json")).toHaveTextContent('{ "a": 1 }');
    });

    it("shows a JSON string that doesn't parse as it is", () => {
      expect(valueCell("not json", "json")).toHaveTextContent("not json");
    });

    it("lists a str[] array", () => {
      vi.spyOn(console, "debug").mockImplementation(() => {});
      const items = within(valueCell(["a", "b"], "str[]")).getAllByRole("listitem");
      expect(items.map((item) => item.textContent)).toEqual(["a", "b"]);
    });

    it("shows a value of an unknown data type as it is", () => {
      expect(valueCell("as is", "unknown" as DataType)).toHaveTextContent("as is");
    });

    it("shows a str[] that isn't an array as a string", () => {
      vi.spyOn(console, "debug").mockImplementation(() => {});
      expect(valueCell("a,b", "str[]")).toHaveTextContent("a,b");
    });
  });
}

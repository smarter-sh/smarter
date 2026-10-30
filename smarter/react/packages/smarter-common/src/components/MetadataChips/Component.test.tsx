import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { Filtering } from "../../lib/Types";
import { AnnotationChips, annotationRequirement, AnnotationsRow, MAX_CHIP_VALUE_LENGTH, TagChips, TagsRow } from ".";

function filtering(narrowed: Partial<Filtering> = {}): Filtering {
  return { tags: [], annotations: [], onTag: vi.fn(), onAnnotation: vi.fn(), ...narrowed };
}

describe("TagChips", () => {
  it("narrows the list by a clicked tag, and shows the applied tag as pressed and disabled", async () => {
    const user = userEvent.setup();
    const narrowing = filtering({ tags: ["production"] });
    render(<TagChips tags={["production", "support"]} filtering={narrowing} />);

    await user.click(screen.getByRole("button", { name: "support" }));
    expect(narrowing.onTag).toHaveBeenCalledWith("support");
    expect(screen.getByRole("button", { name: "support" })).toHaveAttribute(
      "title",
      "Show only the resources tagged support",
    );
    const production = screen.getByRole("button", { name: "production" });
    expect(production).toHaveAttribute("aria-pressed", "true");
    expect(production).toBeDisabled();
  });

  it("shows plain chips without filtering, and says when there are none", () => {
    const { rerender } = render(<TagChips tags={["production"]} />);
    expect(within(screen.getByRole("list", { name: "Tags" })).getByRole("listitem")).toHaveTextContent("production");
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    rerender(<TagChips tags={null} />);
    expect(screen.getByText("No value")).toBeInTheDocument();
  });
});

describe("AnnotationChips", () => {
  it("narrows the list by a clicked annotation's key and value", async () => {
    const user = userEvent.setup();
    const narrowing = filtering({ annotations: [annotationRequirement("acme.com/team", "a")] });
    render(<AnnotationChips annotations={{ "acme.com/id": "A-1", "acme.com/team": "a" }} filtering={narrowing} />);

    await user.click(screen.getByRole("button", { name: "acme.com/id: A-1" }));
    expect(narrowing.onAnnotation).toHaveBeenCalledWith("acme.com/id=A-1");
    expect(screen.getByRole("button", { name: "acme.com/team: a" })).toHaveAttribute("aria-pressed", "true");
  });

  it("shortens a long or multi-line value, shows a key without a value alone, and says when there are none", () => {
    const long = "line one\n" + "x".repeat(MAX_CHIP_VALUE_LENGTH * 2);
    const { rerender } = render(<AnnotationChips annotations={{ "acme.com/note": long, "acme.com/flag": "" }} />);
    const items = within(screen.getByRole("list", { name: "Annotations" })).getAllByRole("listitem");
    // "line one " and as many x as fit before the ellipsis, in MAX_CHIP_VALUE_LENGTH characters.
    const xs = "x".repeat(MAX_CHIP_VALUE_LENGTH - "line one ".length - 1);
    expect(items[0]).toHaveTextContent(new RegExp(`^acme\\.com/note: line one ${xs}…$`));
    expect(items[0]).toHaveAttribute("title", `acme.com/note: ${long}`);
    expect(items[1]).toHaveTextContent(/^acme\.com\/flag$/);
    rerender(<AnnotationChips annotations={{}} />);
    expect(screen.getByText("No value")).toBeInTheDocument();
  });
});

describe("TagsRow and AnnotationsRow", () => {
  it("label a row of a details table", () => {
    render(
      <table>
        <tbody>
          <TagsRow tags={["production"]} />
          <AnnotationsRow annotations={{ "acme.com/id": "A-1" }} label="Labels" />
        </tbody>
      </table>,
    );
    const [tags, annotations] = screen.getAllByRole("row");
    expect(within(tags).getAllByRole("cell")[0]).toHaveTextContent("Tags");
    expect(within(annotations).getAllByRole("cell")[0]).toHaveTextContent("Labels");
  });
});

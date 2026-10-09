import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { Sorting } from "../../lib/Types";
import SortableHeader, { nextOrdering } from "./Component";

function renderHeader(column: string, sorting?: Sorting) {
  return render(
    <table>
      <thead>
        <tr>
          <SortableHeader column={column} sorting={sorting} className="p-1">
            Name
          </SortableHeader>
        </tr>
      </thead>
    </table>,
  );
}

describe("nextOrdering", () => {
  it("sorts ascending, then descending, then in the default order", () => {
    expect(nextOrdering("name", "")).toBe("name");
    expect(nextOrdering("name", "-updatedAt")).toBe("name");
    expect(nextOrdering("name", "name")).toBe("-name");
    expect(nextOrdering("name", "-name")).toBe("");
  });
});

describe("SortableHeader", () => {
  it("is a plain header without a sort", () => {
    renderHeader("name");
    expect(screen.getByRole("columnheader", { name: "Name" })).toHaveClass("p-1");
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("is a plain header for a column that the list api can't sort by", () => {
    renderHeader("name", { ordering: "", sortFields: ["updatedAt"], onSort: vi.fn() });
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("requests the column's next ordering when it is clicked", async () => {
    const onSort = vi.fn();
    renderHeader("name", { ordering: "-updatedAt", sortFields: ["name", "updatedAt"], onSort });
    expect(screen.getByRole("columnheader", { name: "Name" })).toHaveAttribute("aria-sort", "none");

    await userEvent.click(screen.getByRole("button", { name: "Name" }));
    expect(onSort).toHaveBeenCalledWith("name");
  });

  it("says which way its column is sorted", () => {
    const { unmount } = renderHeader("name", { ordering: "name", sortFields: ["name"], onSort: vi.fn() });
    expect(screen.getByRole("columnheader", { name: "Name" })).toHaveAttribute("aria-sort", "ascending");
    unmount();
    renderHeader("name", { ordering: "-name", sortFields: ["name"], onSort: vi.fn() });
    expect(screen.getByRole("columnheader", { name: "Name" })).toHaveAttribute("aria-sort", "descending");
  });
});

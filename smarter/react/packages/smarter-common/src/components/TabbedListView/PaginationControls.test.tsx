import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { PaginationControls } from "./PaginationControls";

const pagination = { page: 2, pageSize: 25, numPages: 3, count: 61, search: "" };

function setup(props: Partial<Parameters<typeof PaginationControls>[0]> = {}) {
  const onPage = vi.fn();
  render(<PaginationControls pagination={pagination} disabled={false} onPage={onPage} {...props} />);
  return { onPage, user: userEvent.setup() };
}

describe("PaginationControls", () => {
  it("shows which objects the page has", () => {
    setup();
    expect(screen.getByText("Showing 26–50 of 61")).toBeInTheDocument();
    expect(screen.getByLabelText("Page number")).toHaveValue(2);
    expect(screen.getByText("of 3")).toBeInTheDocument();
  });

  it("goes to the previous and next pages", async () => {
    const { onPage, user } = setup();
    await user.click(screen.getByRole("button", { name: "Previous page" }));
    await user.click(screen.getByRole("button", { name: "Next page" }));
    expect(onPage.mock.calls).toEqual([[1], [3]]);
  });

  it("has no previous page on the first page, nor next page on the last", () => {
    setup({ pagination: { ...pagination, page: 1, numPages: 1, count: 2 } });
    expect(screen.getByText("Showing 1–2 of 2")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Previous page" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Next page" })).toBeDisabled();
    expect(screen.getByLabelText("Page number")).toBeDisabled();
  });

  it("goes to the page typed into the page number box, on enter or when it loses focus", async () => {
    const { onPage, user } = setup();
    const input = screen.getByLabelText("Page number");
    await user.clear(input);
    await user.type(input, "3{Enter}");
    expect(onPage).toHaveBeenLastCalledWith(3);

    await user.clear(input);
    await user.type(input, "1");
    await user.tab();
    expect(onPage).toHaveBeenLastCalledWith(1);
  });

  it("discards a page that does not exist", async () => {
    const { onPage, user } = setup();
    const input = screen.getByLabelText("Page number");
    for (const page of ["9", "0", "2"]) {
      await user.clear(input);
      await user.type(input, `${page}{Enter}`);
      expect(input).toHaveValue(2);
    }
    expect(onPage).not.toHaveBeenCalled();
  });

  it("is disabled while the page loads", () => {
    setup({ disabled: true });
    for (const name of ["Previous page", "Next page"]) {
      expect(screen.getByRole("button", { name })).toBeDisabled();
    }
    expect(screen.getByLabelText("Page number")).toBeDisabled();
  });
});

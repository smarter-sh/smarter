import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import ToggleButton from "@/components/ToggleButton/Component";

describe("ToggleButton", () => {
  it.each([
    ["list", "List View", "Thumbnail View"],
    ["thumbnail", "Thumbnail View", "List View"],
  ] as const)("highlights the %s view, and switches views", async (viewMode, current, other) => {
    const setViewMode = vi.fn();
    const user = userEvent.setup();
    render(<ToggleButton viewMode={viewMode} setViewMode={setViewMode} />);
    expect(screen.getByRole("button", { name: current })).toHaveClass("btn-primary");
    expect(screen.getByRole("button", { name: other })).toHaveClass("btn-outline-secondary");
    await user.click(screen.getByRole("button", { name: other }));
    await user.click(screen.getByRole("button", { name: current }));
    expect(setViewMode.mock.calls).toEqual([[viewMode === "list" ? "thumbnail" : "list"], [viewMode]]);
  });
});

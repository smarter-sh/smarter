import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import ToggleButton from "./Component";

describe("ToggleButton", () => {
  it("highlights the current view, and switches views", async () => {
    const setViewMode = vi.fn();
    render(<ToggleButton viewMode="list" setViewMode={setViewMode} />);

    expect(screen.getByRole("button", { name: "List View" })).toHaveClass("btn-primary");
    expect(screen.getByRole("button", { name: "Thumbnail View" })).not.toHaveClass("btn-primary");

    await userEvent.click(screen.getByRole("button", { name: "Thumbnail View" }));
    expect(setViewMode).toHaveBeenCalledWith("thumbnail");
  });
});

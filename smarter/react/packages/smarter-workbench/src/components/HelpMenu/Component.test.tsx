import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import HelpMenu from "@/components/HelpMenu/Component";

describe("HelpMenu", () => {
  it("is a button that expands and collapses the list of the workbench's help", async () => {
    const user = userEvent.setup();
    render(<HelpMenu onDocs={() => {}} onTour={() => {}} />);
    const button = screen.getByRole("button", { name: "Help" });
    expect(button).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("list")).not.toBeInTheDocument();

    await user.click(button);
    expect(button).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("list")).toHaveAttribute("id", button.getAttribute("aria-controls"));
    expect(screen.getAllByRole("listitem").map((item) => item.textContent)).toEqual([
      "Technical references",
      "Take the guided tour",
    ]);
    await user.click(button);
    expect(screen.queryByRole("list")).not.toBeInTheDocument();
  });

  it("closes, then opens the Docs dialog or starts the tour", async () => {
    const onDocs = vi.fn();
    const onTour = vi.fn();
    const user = userEvent.setup();
    render(<HelpMenu onDocs={onDocs} onTour={onTour} />);

    await user.click(screen.getByRole("button", { name: "Help" }));
    await user.click(screen.getByRole("button", { name: "Technical references" }));
    expect(onDocs).toHaveBeenCalledOnce();
    expect(screen.queryByRole("list")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Help" }));
    await user.click(screen.getByRole("button", { name: "Take the guided tour" }));
    expect(onTour).toHaveBeenCalledOnce();
    expect(screen.queryByRole("list")).not.toBeInTheDocument();
  });

  it("has no Docs item without onDocs", async () => {
    const user = userEvent.setup();
    render(<HelpMenu onTour={() => {}} />);
    await user.click(screen.getByRole("button", { name: "Help" }));
    expect(screen.getAllByRole("listitem")).toHaveLength(1);
    expect(screen.queryByRole("button", { name: "Technical references" })).not.toBeInTheDocument();
  });

  it("closes on Escape, and returns the focus to its button", async () => {
    const user = userEvent.setup();
    render(<HelpMenu onTour={() => {}} />);
    const button = screen.getByRole("button", { name: "Help" });
    await user.click(button);
    await user.tab();
    expect(screen.getByRole("button", { name: "Take the guided tour" })).toHaveFocus();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("list")).not.toBeInTheDocument();
    expect(button).toHaveFocus();
  });
});

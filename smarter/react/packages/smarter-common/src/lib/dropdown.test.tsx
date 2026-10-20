import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { useDropdown } from "./dropdown";

function Menu() {
  const { open, toggle, close, rootRef, buttonRef, menuId } = useDropdown();
  return (
    <>
      <div ref={rootRef}>
        <button ref={buttonRef} type="button" aria-expanded={open} aria-controls={menuId} onClick={toggle}>
          Help
        </button>
        <div id={menuId} role="menu" hidden={!open}>
          <button type="button" role="menuitem" onClick={close}>
            Docs
          </button>
          <span>Inside</span>
        </div>
      </div>
      <p>Outside</p>
    </>
  );
}

describe("useDropdown", () => {
  it("opens and closes the menu with its button", async () => {
    const user = userEvent.setup();
    render(<Menu />);
    const button = screen.getByRole("button", { name: "Help" });
    expect(button).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();

    await user.click(button);
    expect(button).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("menu")).toHaveAttribute("id", button.getAttribute("aria-controls"));
    await user.click(button);
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });

  it("closes on a click outside it, but not inside it", async () => {
    const user = userEvent.setup();
    render(<Menu />);
    await user.click(screen.getByRole("button", { name: "Help" }));
    await user.click(screen.getByText("Inside"));
    expect(screen.getByRole("menu")).toBeInTheDocument();
    await user.click(screen.getByText("Outside"));
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });

  it("closes on Escape, and returns the focus to its button", async () => {
    const user = userEvent.setup();
    render(<Menu />);
    const button = screen.getByRole("button", { name: "Help" });
    await user.click(button);
    screen.getByRole("menuitem", { name: "Docs" }).focus();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
    expect(button).toHaveFocus();
  });

  it("closes from a menu item", async () => {
    const user = userEvent.setup();
    render(<Menu />);
    await user.click(screen.getByRole("button", { name: "Help" }));
    await user.click(screen.getByRole("menuitem", { name: "Docs" }));
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });
});

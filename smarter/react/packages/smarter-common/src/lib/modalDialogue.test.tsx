import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Modal } from "./modalDialogue";

describe("Modal", () => {
  it("is a dialog, named by its title", () => {
    render(
      <Modal show title="Delete Secret" onOk={() => {}} onCancel={() => {}}>
        Are you sure?
      </Modal>,
    );
    expect(screen.getByRole("dialog", { name: "Delete Secret" })).toHaveTextContent("Are you sure?");
  });

  it("renders nothing when it is not shown", () => {
    render(<Modal show={false} title="Hidden" onClose={() => {}} />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("calls its handlers from its buttons, and OK from the Enter key", async () => {
    const onOk = vi.fn();
    const onCancel = vi.fn();
    const user = userEvent.setup();
    render(<Modal show title="Rename" onOk={onOk} onCancel={onCancel} />);

    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(onCancel).toHaveBeenCalledOnce();
    await user.click(screen.getByRole("button", { name: "OK" }));
    await user.keyboard("{Enter}");
    expect(onOk).toHaveBeenCalledTimes(2);
  });

  it("closes from its close icon", async () => {
    const onClose = vi.fn();
    render(<Modal show title="Error" onClose={onClose} />);
    await userEvent.click(screen.getAllByRole("button", { name: "Close" })[0]);
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("closes on Escape, or a click outside it", async () => {
    const onCancel = vi.fn();
    const user = userEvent.setup();
    render(<Modal show title="Rename" onOk={() => {}} onCancel={onCancel} />);
    await user.keyboard("{Escape}");
    await user.click(screen.getByRole("dialog"));
    expect(onCancel).toHaveBeenCalledTimes(2);
  });

  it("requires a handler", () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() => render(<Modal show title="Nothing" />)).toThrow(/requires at least one/);
  });
});

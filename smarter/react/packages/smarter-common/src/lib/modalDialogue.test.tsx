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

  it("focuses its default button when it opens, and runs it with the Enter key", async () => {
    const onOk = vi.fn();
    const user = userEvent.setup();
    render(
      <>
        <button type="button">Open</button>
        <Modal show title="Delete Secret" onOk={onOk} onCancel={() => {}} />
      </>,
    );
    expect(screen.getByRole("button", { name: "OK" })).toHaveFocus();
    await user.keyboard("{Enter}");
    expect(onOk).toHaveBeenCalledOnce();
  });

  it("closes a dialog without OK, e.g. a result, with the Enter key", async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(<Modal show title="Saved" onClose={onClose} />);
    const close = screen.getAllByRole("button", { name: "Close" })[1];
    expect(close).toHaveFocus();
    await user.keyboard("{Enter}");
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("runs OK with the Enter key in its input, and keeps an input's focus", async () => {
    const onOk = vi.fn();
    const user = userEvent.setup();
    render(
      <Modal show title="Clone Secret" onOk={onOk} onCancel={() => {}}>
        {/* eslint-disable-next-line jsx-a11y/no-autofocus */}
        <input aria-label="New name" autoFocus />
      </Modal>,
    );
    const input = screen.getByRole("textbox", { name: "New name" });
    expect(input).toHaveFocus();
    await user.type(input, "copy{Enter}");
    expect(onOk).toHaveBeenCalledOnce();
  });

  it("leaves Enter to its other buttons: Cancel cancels", async () => {
    const onOk = vi.fn();
    const onCancel = vi.fn();
    const user = userEvent.setup();
    render(<Modal show title="Delete Secret" onOk={onOk} onCancel={onCancel} />);
    screen.getByRole("button", { name: "Cancel" }).focus();
    await user.keyboard("{Enter}");
    expect(onCancel).toHaveBeenCalledOnce();
    expect(onOk).not.toHaveBeenCalled();
  });

  it("runs its default action for Enter outside it, e.g. on the button that opened it", async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();
    const { rerender } = render(
      <>
        <button type="button">Save</button>
        <Modal show={false} title="Saved" onClose={onClose} />
      </>,
    );
    screen.getByRole("button", { name: "Save" }).focus();
    rerender(
      <>
        <button type="button">Save</button>
        <Modal show title="Saved" onClose={onClose} />
      </>,
    );
    screen.getByRole("button", { name: "Save" }).focus();
    await user.keyboard("{Enter}");
    expect(onClose).toHaveBeenCalledOnce();
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

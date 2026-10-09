import { render, screen, waitForElementToBeRemoved } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { fakeEditor } from "@/mocks/fakeEditor";
import { SECRET_YAML } from "@/mocks/fixtures";

import Toolbar from "./Component";

type ToolbarProps = Parameters<typeof Toolbar>[0];

function renderToolbar(props: Partial<ToolbarProps> = {}) {
  const { monacoEditor } = fakeEditor(SECRET_YAML);
  const defaults: ToolbarProps = {
    editor: monacoEditor,
    isDirty: true,
    problemCount: 0,
    isBusy: false,
    fileName: "example.yaml",
    canDelete: true,
    deleteTitle: "Delete: Delete this Secret",
    onSave: vi.fn(),
    onRevert: vi.fn(),
    onClone: vi.fn(),
    onDelete: vi.fn(),
  };
  const allProps = { ...defaults, ...props };
  render(<Toolbar {...allProps} />);
  return allProps;
}

const button = (name: RegExp | string) => screen.getByRole("button", { name });

describe("Toolbar", () => {
  it("explains why it can't save", () => {
    renderToolbar({ isDirty: false });
    expect(button("Save: There are no changes to save")).toBeDisabled();
  });

  it.each([
    [1, "Save: Fix this manifest's problem first"],
    [3, "Save: Fix this manifest's 3 problems first"],
  ])("won't save a manifest with %i problems", (problemCount, title) => {
    renderToolbar({ problemCount });
    expect(button(title)).toBeDisabled();
  });

  it("saves, reverts, clones and deletes with the parent's handlers", async () => {
    const user = userEvent.setup();
    const { onSave, onRevert, onClone, onDelete } = renderToolbar();
    await user.click(button("Save: Apply your changes to this manifest"));
    await user.click(button(/^Revert:/));
    await user.click(button(/^Clone:/));
    await user.click(button("Delete: Delete this Secret"));
    expect(onSave).toHaveBeenCalled();
    expect(onRevert).toHaveBeenCalled();
    expect(onClone).toHaveBeenCalled();
    expect(onDelete).toHaveBeenCalled();
  });

  it("disables its actions while busy", () => {
    renderToolbar({ isBusy: true });
    expect(button(/^Save:/)).toBeDisabled();
    expect(button(/^Revert:/)).toBeDisabled();
    expect(button(/^Clone:/)).toBeDisabled();
    expect(button(/^Delete:/)).toBeDisabled();
  });

  it("undoes and redoes in the editor", async () => {
    const user = userEvent.setup();
    const { editor } = renderToolbar();
    await user.click(button("Undo"));
    await user.click(button("Redo"));
    expect(editor?.trigger).toHaveBeenCalledWith("toolbar", "undo", null);
    expect(editor?.trigger).toHaveBeenCalledWith("toolbar", "redo", null);
  });

  it("copies the manifest, and says so briefly", async () => {
    const user = userEvent.setup();
    renderToolbar();
    await user.click(button(/^Copy:/));
    expect(await navigator.clipboard.readText()).toBe(SECRET_YAML);
    await waitForElementToBeRemoved(() => screen.queryByText("Copied to clipboard"), { timeout: 2000 });
  });

  it("pastes the clipboard over the editor's selection", async () => {
    const user = userEvent.setup();
    const { editor } = renderToolbar();
    await navigator.clipboard.writeText("pasted");
    await user.click(button(/^Paste:/));
    // the paste reads the clipboard asynchronously.
    await vi.waitFor(() => expect(editor?.focus).toHaveBeenCalled());
    expect(editor?.executeEdits).toHaveBeenCalledWith("toolbar", [
      expect.objectContaining({ text: "pasted", forceMoveMarkers: true }),
    ]);
  });

  it("pastes nothing when the editor has no selection", async () => {
    const user = userEvent.setup();
    const { editor, monacoEditor } = fakeEditor(SECRET_YAML);
    editor.getSelection.mockReturnValue(null as never);
    renderToolbar({ editor: monacoEditor });
    await user.click(button(/^Paste:/));
    await vi.waitFor(() => expect(editor.focus).toHaveBeenCalled());
    expect(editor.executeEdits).not.toHaveBeenCalled();
  });

  it("downloads the manifest as a file", async () => {
    const user = userEvent.setup();
    const createObjectURL = vi.fn(() => "blob:manifest");
    const revokeObjectURL = vi.fn();
    vi.stubGlobal("URL", Object.assign(URL, { createObjectURL, revokeObjectURL }));
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    try {
      renderToolbar();
      await user.click(button("Download: Save this manifest as example.yaml"));
      expect(createObjectURL).toHaveBeenCalledWith(expect.any(Blob));
      expect(click).toHaveBeenCalled();
      expect(revokeObjectURL).toHaveBeenCalledWith("blob:manifest");
    } finally {
      vi.unstubAllGlobals();
    }
  });

  it("does nothing in the editor before it mounts", async () => {
    const user = userEvent.setup();
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    renderToolbar({ editor: null });
    await user.click(button("Undo"));
    await user.click(button("Redo"));
    await user.click(button(/^Copy:/));
    await user.click(button(/^Paste:/));
    await user.click(button(/^Download:/));
    expect(click).not.toHaveBeenCalled();
    expect(screen.queryByText("Copied to clipboard")).not.toBeInTheDocument();
  });
});

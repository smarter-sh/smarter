import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type * as monaco from "monaco-editor";
import { describe, expect, it, vi } from "vitest";

import EditorViewToolbar from "@/components/EditorViewToolbar/Component";

const JSON_TEXT = '{\n  "model": "gpt-4o-mini",\n  "messages": [\n    { "role": "user" }\n  ]\n}';

type ContentListener = (event: Partial<monaco.editor.IModelContentChangedEvent>) => void;

/** A fake of the parts of the Monaco editor that the toolbar uses. */
function fakeEditor(value = JSON_TEXT) {
  let listener: ContentListener | null = null;
  const dispose = vi.fn();
  const editor = {
    getValue: vi.fn(() => value),
    trigger: vi.fn(),
    updateOptions: vi.fn(),
    onDidChangeModelContent: vi.fn((callback: ContentListener) => {
      listener = callback;
      return { dispose };
    }),
  };
  const changeContent = (event: Partial<monaco.editor.IModelContentChangedEvent>) => act(() => listener?.(event));
  return { editor, dispose, changeContent, monacoEditor: editor as unknown as monaco.editor.IStandaloneCodeEditor };
}

const button = (name: string) => screen.getByRole("button", { name });

describe("EditorViewToolbar", () => {
  it("wraps long lines, until the user scrolls them", async () => {
    const user = userEvent.setup();
    const { editor, monacoEditor } = fakeEditor();
    render(<EditorViewToolbar editor={monacoEditor} />);
    expect(button("Wrap lines")).toHaveAttribute("aria-pressed", "true");
    expect(editor.updateOptions).toHaveBeenLastCalledWith({ wordWrap: "on" });

    await user.click(button("Wrap lines"));
    expect(button("Wrap lines")).toHaveAttribute("aria-pressed", "false");
    expect(button("Wrap lines")).toHaveAttribute("title", "Wrap long lines");
    expect(editor.updateOptions).toHaveBeenLastCalledWith({ wordWrap: "off" });
  });

  it("folds the JSON below its top-level keys, and expands it again", async () => {
    const user = userEvent.setup();
    const { editor, monacoEditor } = fakeEditor();
    render(<EditorViewToolbar editor={monacoEditor} />);
    expect(button("Expand JSON")).toHaveAttribute("aria-pressed", "true");

    await user.click(button("Expand JSON"));
    expect(editor.trigger.mock.calls.map((call) => call[1])).toEqual(["editor.unfoldAll", "editor.foldLevel2"]);
    expect(button("Expand JSON")).toHaveAttribute("aria-pressed", "false");
    expect(button("Expand JSON")).toHaveAttribute("title", "Expand all the JSON");

    editor.trigger.mockClear();
    await user.click(button("Expand JSON"));
    expect(editor.trigger.mock.calls.map((call) => call[1])).toEqual(["editor.unfoldAll"]);
    expect(button("Expand JSON")).toHaveAttribute("aria-pressed", "true");
  });

  it("is expanded again when the editor's whole text is replaced, but not when it is edited", async () => {
    const user = userEvent.setup();
    const { monacoEditor, changeContent } = fakeEditor();
    render(<EditorViewToolbar editor={monacoEditor} />);
    await user.click(button("Expand JSON"));

    // a keystroke.
    changeContent({ isFlush: false, changes: [{ text: "x" } as monaco.editor.IModelContentChange] });
    expect(button("Expand JSON")).toHaveAttribute("aria-pressed", "false");

    // another template, as @monaco-editor/react's executeEdits() replaces the text.
    changeContent({ isFlush: false, changes: [{ text: JSON_TEXT } as monaco.editor.IModelContentChange] });
    expect(button("Expand JSON")).toHaveAttribute("aria-pressed", "true");

    // a new response, as a read-only editor's setValue() replaces the text.
    await user.click(button("Expand JSON"));
    changeContent({ isFlush: true, changes: [] });
    expect(button("Expand JSON")).toHaveAttribute("aria-pressed", "true");
  });

  it("stops listening to the editor when it unmounts", () => {
    const { dispose, monacoEditor } = fakeEditor();
    const { unmount } = render(<EditorViewToolbar editor={monacoEditor} />);
    unmount();
    expect(dispose).toHaveBeenCalled();
  });

  it("copies the editor's text, and says so briefly", async () => {
    const user = userEvent.setup();
    render(<EditorViewToolbar editor={fakeEditor().monacoEditor} />);
    await user.click(button("Copy the text"));
    expect(await navigator.clipboard.readText()).toBe(JSON_TEXT);
    expect(button("Copied")).toBeInTheDocument();
    await vi.waitFor(() => expect(button("Copy the text")).toBeInTheDocument(), { timeout: 2500 });
  });

  it("logs an error when the clipboard refuses the text", async () => {
    const user = userEvent.setup();
    const error = vi.spyOn(console, "error").mockImplementation(() => {});
    vi.spyOn(navigator.clipboard, "writeText").mockRejectedValueOnce(new Error("denied"));
    render(<EditorViewToolbar editor={fakeEditor().monacoEditor} />);
    await user.click(button("Copy the text"));
    await vi.waitFor(() => expect(error).toHaveBeenCalled());
    expect(button("Copy the text")).toBeInTheDocument();
  });

  it("copies nothing when the editor is empty", async () => {
    const user = userEvent.setup();
    const writeText = vi.spyOn(navigator.clipboard, "writeText");
    render(<EditorViewToolbar editor={fakeEditor("").monacoEditor} />);
    await user.click(button("Copy the text"));
    expect(writeText).not.toHaveBeenCalled();
  });

  it("does nothing in the editor before it mounts", async () => {
    const user = userEvent.setup();
    render(<EditorViewToolbar editor={null} />);
    for (const name of ["Wrap lines", "Expand JSON", "Copy the text"]) {
      await user.click(button(name));
    }
    expect(button("Expand JSON")).toHaveAttribute("aria-pressed", "true");
    expect(button("Copy the text")).toBeInTheDocument();
  });
});

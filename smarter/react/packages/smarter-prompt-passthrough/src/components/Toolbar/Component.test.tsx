import { render, screen, waitForElementToBeRemoved } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type * as monaco from "monaco-editor";
import { describe, expect, it, vi } from "vitest";

import Toolbar from "@/components/Toolbar/Component";

const REQUEST = '{"model": "gpt-4o-mini"}';

/** A fake of the parts of the Monaco editor that the toolbar uses. */
function fakeEditor(value = REQUEST) {
  const format = { run: vi.fn() };
  const editor = {
    getValue: vi.fn(() => value),
    setValue: vi.fn(),
    trigger: vi.fn(),
    getAction: vi.fn(() => format),
  };
  return { editor, format, monacoEditor: editor as unknown as monaco.editor.IStandaloneCodeEditor };
}

const button = (name: string) => screen.getByRole("button", { name });

describe("Toolbar", () => {
  it("clears, formats, undoes and redoes in the editor", async () => {
    const user = userEvent.setup();
    const { editor, format, monacoEditor } = fakeEditor();
    render(<Toolbar editor={monacoEditor} />);
    await user.click(button("File New"));
    await user.click(button("Format JSON"));
    await user.click(button("Undo"));
    await user.click(button("Redo"));
    expect(editor.setValue).toHaveBeenCalledWith("");
    expect(editor.getAction).toHaveBeenCalledWith("editor.action.formatDocument");
    expect(format.run).toHaveBeenCalled();
    expect(editor.trigger).toHaveBeenCalledWith("", "undo", null);
    expect(editor.trigger).toHaveBeenCalledWith("", "redo", null);
  });

  it("copies the request, and says so briefly", async () => {
    vi.spyOn(console, "debug").mockImplementation(() => {});
    const user = userEvent.setup();
    render(<Toolbar editor={fakeEditor().monacoEditor} />);
    await user.click(button("Copy JSON"));
    expect(await navigator.clipboard.readText()).toBe(REQUEST);
    await waitForElementToBeRemoved(() => screen.queryByText("Copied to clipboard"), { timeout: 2000 });
  });

  it("copies and saves nothing when the editor is empty", async () => {
    const user = userEvent.setup();
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    render(<Toolbar editor={fakeEditor("").monacoEditor} />);
    await user.click(button("Copy JSON"));
    await user.click(button("File Save"));
    expect(screen.queryByText("Copied to clipboard")).not.toBeInTheDocument();
    expect(click).not.toHaveBeenCalled();
  });

  it("saves the request as a file", async () => {
    const user = userEvent.setup();
    const createObjectURL = vi.fn(() => "blob:request");
    const revokeObjectURL = vi.fn();
    vi.stubGlobal("URL", Object.assign(URL, { createObjectURL, revokeObjectURL }));
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    try {
      render(<Toolbar editor={fakeEditor().monacoEditor} />);
      await user.click(button("File Save"));
      expect(createObjectURL).toHaveBeenCalledWith(expect.any(Blob));
      expect(click).toHaveBeenCalled();
      expect(revokeObjectURL).toHaveBeenCalledWith("blob:request");
    } finally {
      vi.unstubAllGlobals();
    }
  });

  it("opens a JSON file into the editor", async () => {
    const user = userEvent.setup();
    const { editor, monacoEditor } = fakeEditor();
    // the file inputs that the toolbar opens.
    const inputs: HTMLInputElement[] = [];
    vi.spyOn(HTMLInputElement.prototype, "click").mockImplementation(function (this: HTMLInputElement) {
      inputs.push(this);
    });
    render(<Toolbar editor={monacoEditor} />);
    await user.click(button("File Open"));
    const [input] = inputs;
    expect(input.accept).toBe(".json,application/json");

    // the user picks a file.
    const file = new File(['{"opened": true}'], "request.json", { type: "application/json" });
    Object.defineProperty(input, "files", { value: [file] });
    input.dispatchEvent(new Event("change"));
    await vi.waitFor(() => expect(editor.setValue).toHaveBeenCalledWith('{"opened": true}'));
  });

  it("opens nothing when the user picks no file", async () => {
    const user = userEvent.setup();
    const { editor, monacoEditor } = fakeEditor();
    // the file inputs that the toolbar opens.
    const inputs: HTMLInputElement[] = [];
    vi.spyOn(HTMLInputElement.prototype, "click").mockImplementation(function (this: HTMLInputElement) {
      inputs.push(this);
    });
    render(<Toolbar editor={monacoEditor} />);
    await user.click(button("File Open"));
    const [input] = inputs;
    Object.defineProperty(input, "files", { value: [] });
    input.dispatchEvent(new Event("change"));
    expect(editor.setValue).not.toHaveBeenCalled();
  });

  it("does nothing in the editor before it mounts", async () => {
    const user = userEvent.setup();
    render(<Toolbar editor={null} />);
    for (const name of ["File New", "Format JSON", "Undo", "Redo", "Copy JSON", "File Save"]) {
      await user.click(button(name));
    }
    expect(screen.queryByText("Copied to clipboard")).not.toBeInTheDocument();
  });
});

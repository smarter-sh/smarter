import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { fakeEditor } from "@/mocks/fakeEditor";
import { SECRET_YAML } from "@/mocks/fixtures";
import type { ManifestError } from "@/lib/validation";

import ManifestEditor from "./Component";

// a fake of @monaco-editor/react's Editor, which mounts the fake editor of each test.
const mount = vi.hoisted(() => ({ editor: null as unknown, monaco: null as unknown }));
vi.mock("@monaco-editor/react", async () => {
  const { useEffect } = await import("react");
  type Props = {
    height: string;
    value: string;
    beforeMount: (monaco: unknown) => void;
    onMount: (editor: unknown, monaco: unknown) => void;
    onChange: (value: string | undefined) => void;
  };
  return {
    default: function Editor({ height, value, beforeMount, onMount, onChange }: Props) {
      useEffect(() => {
        beforeMount(mount.monaco);
        onMount(mount.editor, mount.monaco);
        // eslint-disable-next-line react-hooks/exhaustive-deps
      }, []);
      return (
        <div>
          <span>height {height}</span>
          <button type="button" onClick={() => onChange(value + "\n# edited")}>
            Type
          </button>
          <button type="button" onClick={() => onChange(undefined)}>
            Clear
          </button>
        </div>
      );
    },
  };
});

function fakeMonaco() {
  return {
    MarkerSeverity: { Error: 8 },
    Range: class {},
    KeyCode: {},
    editor: { defineTheme: vi.fn(), setModelMarkers: vi.fn(), TrackedRangeStickiness: {} },
  };
}

const errors: ManifestError[] = [
  { source: "sam", message: "too short", offset: SECRET_YAML.indexOf("value:"), loc: ["spec", "config", "value"] },
  { source: "yaml", message: "bad indentation", offset: 0, loc: [] },
];

function setUp({ withModel = true } = {}) {
  const fake = fakeEditor(SECRET_YAML, { withModel });
  const monaco = fakeMonaco();
  mount.editor = fake.monacoEditor;
  mount.monaco = monaco;
  const onEditorDidMount = vi.fn();
  const onChange = vi.fn();
  const props = { value: SECRET_YAML, errors, onEditorDidMount, onChange };
  const { rerender } = render(<ManifestEditor {...props} editor={null} />);
  // the parent passes the editor back once it mounts.
  rerender(<ManifestEditor {...props} editor={fake.monacoEditor} />);
  return { ...fake, monaco, onEditorDidMount, onChange };
}

describe("ManifestEditor", () => {
  it("defines its theme, and hands the parent the editor when it mounts", () => {
    const { monaco, monacoEditor, onEditorDidMount } = setUp();
    expect(monaco.editor.defineTheme).toHaveBeenCalledWith("smarter-manifest", expect.any(Object));
    expect(onEditorDidMount).toHaveBeenCalledWith(monacoEditor);
  });

  it("marks each error from its position to the end of its line", () => {
    const { monaco } = setUp();
    expect(monaco.editor.setModelMarkers).toHaveBeenLastCalledWith(expect.anything(), "smarter-manifest", [
      expect.objectContaining({
        message: "too short",
        source: "Smarter manifest",
        startLineNumber: 9,
        startColumn: 5,
        endColumn: "    value: not-a-real-secret".length + 1,
      }),
      expect.objectContaining({ message: "bad indentation", source: "YAML", startLineNumber: 1 }),
    ]);
  });

  it("marks nothing in an editor without a model", () => {
    const { monaco } = setUp({ withModel: false });
    expect(monaco.editor.setModelMarkers).not.toHaveBeenCalled();
  });

  it("grows with its content, between its minimum height and most of the window", () => {
    const { editor } = setUp();
    expect(screen.getByText("height 400px")).toBeInTheDocument();
    act(() => editor.resizeContent(100));
    expect(screen.getByText("height 300px")).toBeInTheDocument();
    act(() => editor.resizeContent(100_000));
    expect(screen.getByText(`height ${Math.round(window.innerHeight * 0.75)}px`)).toBeInTheDocument();
  });

  it("passes edits to the parent", async () => {
    const user = userEvent.setup();
    const { onChange } = setUp();
    await user.click(screen.getByRole("button", { name: "Type" }));
    expect(onChange).toHaveBeenLastCalledWith(`${SECRET_YAML}\n# edited`);
    await user.click(screen.getByRole("button", { name: "Clear" }));
    expect(onChange).toHaveBeenLastCalledWith("");
  });

  it("copies the manifest", async () => {
    const user = userEvent.setup();
    setUp();
    await user.click(screen.getByRole("button", { name: /^Copy:/ }));
    expect(await navigator.clipboard.readText()).toBe(SECRET_YAML);
  });
});

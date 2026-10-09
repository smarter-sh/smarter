import { renderHook } from "@testing-library/react";
import type { Monaco } from "@monaco-editor/react";
import type * as monaco from "monaco-editor";
import { describe, expect, it, vi } from "vitest";

import { useLockedFields } from "./useLockedFields";

/*
 * A minimal fake of the parts of Monaco that useLockedFields uses. Monaco itself loads from a CDN at
 * runtime, which jsdom cannot do. Positions are 1-based lines and columns, as in Monaco.
 */
class Position {
  constructor(
    public lineNumber: number,
    public column: number,
  ) {}
  equals(other: Position) {
    return this.lineNumber === other.lineNumber && this.column === other.column;
  }
  isBefore(other: Position) {
    return this.lineNumber < other.lineNumber || (this.lineNumber === other.lineNumber && this.column < other.column);
  }
}

class Range {
  constructor(
    public startLineNumber: number,
    public startColumn: number,
    public endLineNumber: number,
    public endColumn: number,
  ) {}
  getStartPosition() {
    return new Position(this.startLineNumber, this.startColumn);
  }
  getEndPosition() {
    return new Position(this.endLineNumber, this.endColumn);
  }
  containsPosition(position: Position) {
    return !position.isBefore(this.getStartPosition()) && !this.getEndPosition().isBefore(position);
  }
  static areIntersecting(a: Range, b: Range) {
    return a.getStartPosition().isBefore(b.getEndPosition()) && b.getStartPosition().isBefore(a.getEndPosition());
  }
}

class Selection extends Range {
  getPosition() {
    return this.getEndPosition();
  }
  isEmpty() {
    return this.getStartPosition().equals(this.getEndPosition());
  }
}

const KeyCode = { Backspace: 1, Tab: 2, Enter: 3, LeftArrow: 15, Delete: 20, KeyA: 31, KeyV: 52, KeyX: 54 };

const fakeMonaco = {
  Range,
  KeyCode,
  editor: { TrackedRangeStickiness: { NeverGrowsWhenTypingAtEdges: 1 } },
} as unknown as Monaco;

const MANIFEST = `apiVersion: smarter.sh/v1
kind: Secret
metadata:
  name: example
  description: An example.
spec:
  value: abc
status:
  created: now
`;

// a manifest that has every locked field, each with a scalar value.
const FULL_MANIFEST = `apiVersion: smarter.sh/v1
kind: Plugin
metadata:
  name: example
  pluginClass: static
status: active
`;

class FakeModel {
  private listeners: ((e: { isFlush: boolean }) => void)[] = [];
  constructor(public text: string) {}
  getValue() {
    return this.text;
  }
  getPositionAt(offset: number) {
    const lines = this.text.slice(0, offset).split("\n");
    return new Position(lines.length, lines[lines.length - 1].length + 1);
  }
  getOffsetAt(position: Position) {
    const lines = this.text.split("\n").slice(0, position.lineNumber - 1);
    return lines.reduce((sum, line) => sum + line.length + 1, 0) + position.column - 1;
  }
  getValueInRange(range: Range) {
    return this.text.slice(this.getOffsetAt(range.getStartPosition()), this.getOffsetAt(range.getEndPosition()));
  }
  onDidChangeContent(listener: (e: { isFlush: boolean }) => void) {
    this.listeners.push(listener);
    return { dispose: () => (this.listeners = this.listeners.filter((l) => l !== listener)) };
  }
  change(text: string, isFlush = false) {
    this.text = text;
    this.listeners.forEach((listener) => listener({ isFlush }));
  }
  get listenerCount() {
    return this.listeners.length;
  }
}

function fakeEditor(text = MANIFEST, { messageController = true } = {}) {
  const model = new FakeModel(text);
  const decorations = {
    ranges: [] as Range[],
    set: vi.fn((items: { range: Range }[]) => (decorations.ranges = items.map((item) => item.range))),
    getRanges: () => decorations.ranges,
    clear: vi.fn(() => (decorations.ranges = [])),
  };
  const keyDownListeners: ((e: unknown) => void)[] = [];
  const history: string[] = [];
  const showMessage = vi.fn();
  const editor = {
    selections: [] as Selection[] | null,
    position: new Position(1, 1) as Position | null,
    getModel: () => model,
    createDecorationsCollection: () => decorations,
    onKeyDown: (listener: (e: unknown) => void) => {
      keyDownListeners.push(listener);
      return { dispose: () => keyDownListeners.splice(keyDownListeners.indexOf(listener), 1) };
    },
    getSelections: () => editor.selections,
    getPosition: () => editor.position,
    getContribution: () => (messageController ? { showMessage } : null),
    // the fake's undo restores the text before the last change.
    trigger: vi.fn(() => model.change(history.pop() ?? model.text)),
    /** Make a change that the editor can undo. */
    edit(newText: string) {
      history.push(model.text);
      model.change(newText);
    },
    /** Press a key with the cursor or selection at the given ranges, and say whether the key was prevented. */
    press(
      keyCode: number,
      key: string,
      selections: Selection[],
      modifiers: { ctrlKey?: boolean; metaKey?: boolean } = {},
    ) {
      editor.selections = selections;
      const e = {
        keyCode,
        ctrlKey: false,
        metaKey: false,
        ...modifiers,
        browserEvent: { key },
        preventDefault: vi.fn(),
        stopPropagation: vi.fn(),
      };
      keyDownListeners.forEach((listener) => listener(e));
      return e.preventDefault.mock.calls.length > 0;
    },
    keyDownListenerCount: () => keyDownListeners.length,
  };
  return { editor, model, decorations, showMessage };
}

function lock(fake: ReturnType<typeof fakeEditor>) {
  return renderHook(() => useLockedFields(fake.editor as unknown as monaco.editor.IStandaloneCodeEditor, fakeMonaco));
}

/** A cursor at a line and column. */
const cursor = (line: number, column: number) => new Selection(line, column, line, column);

const flushMicrotasks = () => new Promise((resolve) => setTimeout(resolve, 0));

describe("useLockedFields", () => {
  it("does nothing without an editor", () => {
    expect(() => renderHook(() => useLockedFields(null, null))).not.toThrow();
  });

  it("does nothing without a model", () => {
    const fake = fakeEditor();
    fake.editor.getModel = () => null as unknown as FakeModel;
    lock(fake);
    expect(fake.decorations.set).not.toHaveBeenCalled();
  });

  it("decorates the locked fields that the manifest has", () => {
    const fake = fakeEditor();
    lock(fake);
    const texts = fake.decorations.ranges.map((range) => fake.model.getValueInRange(range));
    // status is a mapping here, not a scalar, so it is not decorated.
    expect(texts).toEqual(["apiVersion: smarter.sh/v1", "kind: Secret", "name: example"]);
  });

  it("ignores keys that don't edit", () => {
    const fake = fakeEditor();
    lock(fake);
    expect(fake.editor.press(KeyCode.LeftArrow, "ArrowLeft", [cursor(1, 3)])).toBe(false);
    expect(fake.editor.press(KeyCode.KeyA, "a", [cursor(1, 3)], { ctrlKey: true })).toBe(false);
  });

  it("prevents typing in a locked field, with Monaco's read-only message", () => {
    const fake = fakeEditor();
    lock(fake);
    expect(fake.editor.press(KeyCode.KeyA, "a", [cursor(2, 8)])).toBe(true);
    expect(fake.showMessage).toHaveBeenCalledWith(expect.stringContaining("cannot be changed"), new Position(2, 8));
  });

  it("allows typing outside the locked fields", () => {
    const fake = fakeEditor();
    lock(fake);
    expect(fake.editor.press(KeyCode.KeyA, "a", [cursor(5, 18)])).toBe(false);
    expect(fake.editor.press(KeyCode.Backspace, "Backspace", [cursor(7, 10)])).toBe(false);
  });

  it("checks every cursor", () => {
    const fake = fakeEditor();
    lock(fake);
    expect(fake.editor.press(KeyCode.Delete, "Delete", [cursor(5, 18), cursor(1, 3)])).toBe(true);
  });

  it("prevents a cut or paste of a selection that overlaps a locked field", () => {
    const fake = fakeEditor();
    lock(fake);
    expect(fake.editor.press(KeyCode.KeyX, "x", [new Selection(1, 5, 2, 3)], { metaKey: true })).toBe(true);
    expect(fake.editor.press(KeyCode.KeyV, "v", [new Selection(5, 3, 7, 5)], { ctrlKey: true })).toBe(false);
  });

  it("allows a new line at either end of a locked field, but not inside it", () => {
    const fake = fakeEditor();
    lock(fake);
    expect(fake.editor.press(KeyCode.Enter, "Enter", [cursor(2, 1)])).toBe(false);
    expect(fake.editor.press(KeyCode.Enter, "Enter", [cursor(2, 13)])).toBe(false);
    expect(fake.editor.press(KeyCode.Enter, "Enter", [cursor(2, 6)])).toBe(true);
    expect(fake.editor.press(KeyCode.Tab, "Tab", [cursor(5, 3)])).toBe(false);
  });

  it("allows keys when the editor has no selections", () => {
    const fake = fakeEditor();
    lock(fake);
    expect(fake.editor.press(KeyCode.KeyA, "a", null as unknown as Selection[])).toBe(false);
  });

  it("prevents an edit without a message when Monaco has no message controller", () => {
    const fake = fakeEditor(MANIFEST, { messageController: false });
    lock(fake);
    expect(fake.editor.press(KeyCode.KeyA, "a", [cursor(2, 8)])).toBe(true);
    expect(fake.showMessage).not.toHaveBeenCalled();
  });

  it("leaves other changes alone", async () => {
    const fake = fakeEditor();
    lock(fake);
    fake.editor.edit(MANIFEST.replace("An example.", "An edit."));
    await flushMicrotasks();
    expect(fake.editor.trigger).not.toHaveBeenCalled();
  });

  it("undoes a change to a locked field", async () => {
    const fake = fakeEditor();
    lock(fake);
    fake.editor.edit(MANIFEST.replace("kind: Secret", "kind: Plugin"));
    await flushMicrotasks();
    expect(fake.editor.trigger).toHaveBeenCalledWith("locked-fields", "undo", null);
    expect(fake.model.getValue()).toBe(MANIFEST);
    expect(fake.showMessage).toHaveBeenCalled();
  });

  it("undoes a change that removed a locked field, without a message when there is no cursor", async () => {
    const fake = fakeEditor(FULL_MANIFEST);
    lock(fake);
    expect(fake.decorations.ranges).toHaveLength(5);
    fake.editor.position = null;
    // a decoration collapses when its text is deleted.
    fake.decorations.ranges = fake.decorations.ranges.slice(1);
    fake.editor.edit(FULL_MANIFEST.replace("apiVersion: smarter.sh/v1\n", ""));
    await flushMicrotasks();
    expect(fake.editor.trigger).toHaveBeenCalledTimes(1);
    expect(fake.decorations.ranges).toHaveLength(5);
    expect(fake.showMessage).not.toHaveBeenCalled();
  });

  it("keeps its decorations after an undo unless it finds every locked field", async () => {
    const fake = fakeEditor();
    lock(fake);
    const before = fake.decorations.set.mock.calls.length;
    // an undo that doesn't restore the locked fields, e.g. after a syntax error elsewhere.
    fake.editor.trigger.mockImplementation(() => fake.model.change("kind: [unclosed"));
    fake.editor.edit(MANIFEST.replace("kind: Secret", "kind: Plugin"));
    await flushMicrotasks();
    expect(fake.decorations.set).toHaveBeenCalledTimes(before);
  });

  it("locks the fields of a new text", () => {
    const fake = fakeEditor();
    lock(fake);
    fake.model.change("apiVersion: v2\nkind: Plugin\n", true);
    const texts = fake.decorations.ranges.map((range) => fake.model.getValueInRange(range));
    expect(texts).toEqual(["apiVersion: v2", "kind: Plugin"]);
  });

  it("stops listening when it unmounts", () => {
    const fake = fakeEditor();
    const { unmount } = lock(fake);
    unmount();
    expect(fake.model.listenerCount).toBe(0);
    expect(fake.editor.keyDownListenerCount()).toBe(0);
    expect(fake.decorations.clear).toHaveBeenCalled();
  });
});

/**
 * A fake Monaco editor, for tests of the components that use the editor directly. Monaco loads
 * from a CDN at runtime, which jsdom cannot do. It has only what the components use, with a
 * model whose positions are 1-based lines and columns, as in Monaco.
 */
import type * as monaco from "monaco-editor";
import { vi } from "vitest";

export function fakeModel(text: string) {
  const positionAt = (offset: number) => {
    const lines = text.slice(0, offset).split("\n");
    return { lineNumber: lines.length, column: lines[lines.length - 1].length + 1 };
  };
  return {
    getValue: () => text,
    getPositionAt: vi.fn(positionAt),
    getLineMaxColumn: (lineNumber: number) => text.split("\n")[lineNumber - 1].length + 1,
    getValueInRange: () => "",
    onDidChangeContent: () => ({ dispose: () => {} }),
  };
}

export function fakeEditor(text: string, { withModel = true } = {}) {
  const model = fakeModel(text);
  const contentSizeListeners: ((e: { contentHeight: number }) => void)[] = [];
  const editor = {
    getModel: () => (withModel ? model : null),
    getValue: () => text,
    getSelection: vi.fn(() => ({ startLineNumber: 1, startColumn: 1, endLineNumber: 1, endColumn: 1 })),
    executeEdits: vi.fn(),
    trigger: vi.fn(),
    focus: vi.fn(),
    setValue: vi.fn(),
    setPosition: vi.fn(),
    revealLineInCenter: vi.fn(),
    getContentHeight: () => 400,
    onDidContentSizeChange: (listener: (e: { contentHeight: number }) => void) => {
      contentSizeListeners.push(listener);
      return { dispose: () => {} };
    },
    getContribution: () => null,
    createDecorationsCollection: () => ({ set: () => {}, getRanges: () => [], clear: () => {} }),
    onKeyDown: () => ({ dispose: () => {} }),
    /** Resize the editor's content, as Monaco does as the text grows. */
    resizeContent: (contentHeight: number) => contentSizeListeners.forEach((listener) => listener({ contentHeight })),
  };
  return { editor, model, monacoEditor: editor as unknown as monaco.editor.IStandaloneCodeEditor };
}

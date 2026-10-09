/**
 * Lock a manifest's identifying fields in the Monaco editor: apiVersion, kind and metadata.name.
 *
 * Changing them would make the manifest describe another resource, or none. Monaco has no
 * read-only ranges, so the fields are Monaco decorations, which move with the text as the user
 * edits around them, and:
 *
 * - keystrokes that would change a locked field are prevented, with Monaco's read-only message;
 * - any other change to a locked field, e.g. a paste, a drag and drop or a find and replace, is undone.
 */
import { useEffect } from "react";
import type { Monaco } from "@monaco-editor/react";
import type * as monaco from "monaco-editor";

import { yamlKeys } from "@/lib/validation";

/** The paths of the locked fields. */
export const LOCKED_PATHS: string[][] = [
  ["apiVersion"],
  ["kind"],
  ["metadata", "name"],
  ["metadata", "pluginClass"],
  ["status"],
];

const LOCKED_MESSAGE = "This field identifies this resource and cannot be changed here. Also, status is read-only.";

type MessageController = { showMessage?: (message: string, position: monaco.IPosition) => void };

/** Show Monaco's inline message, the one that it shows for an edit of a read-only editor. */
function showMessage(editor: monaco.editor.IStandaloneCodeEditor, position: monaco.IPosition) {
  const controller = editor.getContribution("editor.contrib.messageController") as MessageController | null;
  controller?.showMessage?.(LOCKED_MESSAGE, position);
}

export function useLockedFields(editor: monaco.editor.IStandaloneCodeEditor | null, monacoInstance: Monaco | null) {
  useEffect(() => {
    const model = editor?.getModel();
    if (!editor || !monacoInstance || !model) return;

    const decorations = editor.createDecorationsCollection();
    let lockedTexts: string[] = [];
    let isUndoing = false;

    // decorate the locked fields of the model's current text, from each key to the end of its value.
    // With onlyIfAll, keep the current decorations unless all of the fields are found, e.g. while
    // the YAML has a syntax error elsewhere.
    const lock = (onlyIfAll = false) => {
      const keys = yamlKeys(model.getValue());
      const found = LOCKED_PATHS.filter((path) => keys.get(path.join("."))?.end !== undefined);
      if (onlyIfAll && found.length !== LOCKED_PATHS.length) return;
      decorations.set(
        found.flatMap((path) => {
          const key = keys.get(path.join("."));
          if (!key || key.end === undefined) return [];
          const start = model.getPositionAt(key.start);
          const end = model.getPositionAt(key.end);
          return [
            {
              range: new monacoInstance.Range(start.lineNumber, start.column, end.lineNumber, end.column),
              options: {
                inlineClassName: "manifest-editor-locked",
                stickiness: monacoInstance.editor.TrackedRangeStickiness.NeverGrowsWhenTypingAtEdges,
                hoverMessage: { value: `**${path.join(".")}** is locked. ${LOCKED_MESSAGE}` },
              },
            },
          ];
        }),
      );
      lockedTexts = decorations.getRanges().map((range) => model.getValueInRange(range));
    };
    lock();

    // prevent the keystrokes that would change a locked field.
    const keyDown = editor.onKeyDown((e) => {
      const { KeyCode } = monacoInstance;
      const isCutOrPaste = (e.ctrlKey || e.metaKey) && (e.keyCode === KeyCode.KeyX || e.keyCode === KeyCode.KeyV);
      const isPrintable = e.browserEvent.key.length === 1 && !e.ctrlKey && !e.metaKey;
      const isEdit = [KeyCode.Backspace, KeyCode.Delete, KeyCode.Enter, KeyCode.Tab].includes(e.keyCode);
      if (!isCutOrPaste && !isPrintable && !isEdit) return;

      const ranges = decorations.getRanges();
      for (const selection of editor.getSelections() ?? []) {
        const position = selection.getPosition();
        const blocked = ranges.some((range) => {
          if (!selection.isEmpty()) return monacoInstance.Range.areIntersecting(selection, range);
          // a new line at either end of a locked field does not change it.
          if (e.keyCode === KeyCode.Enter) {
            return (
              range.containsPosition(position) &&
              !position.equals(range.getStartPosition()) &&
              !position.equals(range.getEndPosition())
            );
          }
          return range.containsPosition(position);
        });
        if (blocked) {
          e.preventDefault();
          e.stopPropagation();
          showMessage(editor, position);
          return;
        }
      }
    });

    // undo any other change to a locked field. A flush, i.e. setValue(), e.g. a revert, is a new text: lock it.
    const contentChange = model.onDidChangeContent((e) => {
      if (e.isFlush) {
        lock();
        return;
      }
      if (isUndoing) return;
      const ranges = decorations.getRanges();
      const changed =
        ranges.length !== lockedTexts.length ||
        ranges.some((range, i) => model.getValueInRange(range) !== lockedTexts[i]);
      if (!changed) return;
      const position = editor.getPosition();
      isUndoing = true;
      queueMicrotask(() => {
        editor.trigger("locked-fields", "undo", null);
        // the undo restores the text, but not a decoration that collapsed when its text was deleted.
        lock(true);
        isUndoing = false;
        if (position) showMessage(editor, position);
      });
    });

    return () => {
      keyDown.dispose();
      contentChange.dispose();
      decorations.clear();
    };
  }, [editor, monacoInstance]);
}

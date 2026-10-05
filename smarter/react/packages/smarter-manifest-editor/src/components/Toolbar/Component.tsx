/**
 * Toolbar Component
 *
 * The manifest editor's toolbar: a Bootstrap button toolbar, of button groups for save; undo and redo;
 * copy and paste; revert and download; and clone and delete. It is the header of the editor's card.
 *
 * Saving, cloning and deleting are handled by the parent, with the cli api. The other
 * buttons work on the Monaco editor directly.
 */
import type * as monaco from "monaco-editor";

import { useCopy } from "@/lib/useCopy";

import "./styles.css";

// the most paths that a Keenicons duotone icon in this toolbar has: ki-trash has 5.
const DUOTONE_PATHS = [1, 2, 3, 4, 5];

interface ToolbarButtonProps {
  onClick: () => void;
  title: string;
  iconClass: string;
  disabled?: boolean;
}

function ToolbarButton({ onClick, title, iconClass, disabled = false }: ToolbarButtonProps) {
  return (
    <button
      type="button"
      className="btn btn-sm btn-icon btn-outline-secondary"
      onClick={onClick}
      title={title}
      disabled={disabled}
    >
      <i className={iconClass}>
        {DUOTONE_PATHS.map((n) => (
          <span key={n} className={`path${n}`}></span>
        ))}
      </i>
    </button>
  );
}

interface CopiedMessageProps {
  show: boolean;
}

/** The same "Copied to clipboard" message as @smarter/prompt-passthrough's toolbar. */
export function CopiedMessage({ show }: CopiedMessageProps) {
  if (!show) return null;
  return <div className="manifest-editor-copied">Copied to clipboard</div>;
}

interface ToolbarProps {
  editor: monaco.editor.IStandaloneCodeEditor | null;
  isDirty: boolean;
  problemCount: number;
  isBusy: boolean;
  fileName: string;
  canDelete: boolean;
  deleteTitle: string;
  onSave: () => void;
  onRevert: () => void;
  onClone: () => void;
  onDelete: () => void;
}

function Toolbar({
  editor,
  isDirty,
  problemCount,
  isBusy,
  fileName,
  canDelete,
  deleteTitle,
  onSave,
  onRevert,
  onClone,
  onDelete,
}: ToolbarProps) {
  const { copied, copy } = useCopy(editor);

  const handleUndo = () => editor?.trigger("toolbar", "undo", null);
  const handleRedo = () => editor?.trigger("toolbar", "redo", null);

  const handlePaste = async () => {
    if (!editor) return;
    const text = await navigator.clipboard.readText();
    const selection = editor.getSelection();
    if (selection) {
      editor.executeEdits("toolbar", [{ range: selection, text, forceMoveMarkers: true }]);
    }
    editor.focus();
  };

  const handleDownload = () => {
    const value = editor?.getValue();
    if (!value) return;
    const url = URL.createObjectURL(new Blob([value], { type: "application/yaml" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = fileName;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="btn-toolbar manifest-editor-toolbar position-relative" role="toolbar" aria-label="Manifest editor">
      <div className="btn-group me-2" role="group" aria-label="Save">
        <ToolbarButton
          onClick={onSave}
          title={
            !isDirty
              ? "Save: There are no changes to save"
              : problemCount
                ? `Save: Fix this manifest's ${problemCount === 1 ? "problem" : `${problemCount} problems`} first`
                : "Save: Apply your changes to this manifest"
          }
          iconClass="bi bi-floppy fs-2"
          disabled={!isDirty || problemCount > 0 || isBusy}
        />
      </div>
      <div className="btn-group me-2" role="group" aria-label="History">
        <ToolbarButton onClick={handleUndo} title="Undo" iconClass="ki-duotone ki-arrow-circle-left fs-2" />
        <ToolbarButton onClick={handleRedo} title="Redo" iconClass="ki-duotone ki-arrow-circle-right fs-2" />
      </div>
      <div className="btn-group me-2" role="group" aria-label="Clipboard">
        <ToolbarButton
          onClick={copy}
          title="Copy: Copy this manifest to the clipboard"
          iconClass={`ki-duotone ${copied ? "ki-copy-success" : "ki-copy"} fs-2`}
        />
        <ToolbarButton
          onClick={handlePaste}
          title="Paste: Paste from the clipboard into this manifest"
          iconClass="ki-duotone ki-clipboard fs-2"
        />
      </div>
      <div className="btn-group me-2" role="group" aria-label="File">
        <ToolbarButton
          onClick={onRevert}
          title="Revert: Discard your changes to this manifest"
          iconClass="ki-duotone ki-arrows-circle fs-2"
          disabled={!isDirty || isBusy}
        />
        <ToolbarButton
          onClick={handleDownload}
          title={`Download: Save this manifest as ${fileName}`}
          iconClass="ki-duotone ki-file-down fs-2"
        />
      </div>
      <div className="btn-group" role="group" aria-label="Resource">
        <ToolbarButton
          onClick={onClone}
          title="Clone: Create a copy of this resource, with a new name"
          iconClass="ki-duotone ki-file-added fs-2"
          disabled={isBusy}
        />
        <ToolbarButton
          onClick={onDelete}
          title={deleteTitle}
          iconClass="ki-duotone ki-trash fs-2"
          disabled={!canDelete || isBusy}
        />
      </div>
      <CopiedMessage show={copied} />
    </div>
  );
}

export default Toolbar;

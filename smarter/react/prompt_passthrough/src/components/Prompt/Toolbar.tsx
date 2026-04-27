import type * as monaco from "monaco-editor";

interface ToolbarProps {
  editor: monaco.editor.IStandaloneCodeEditor | null;
}

function Toolbar({ editor }: ToolbarProps) {
  const handleFormat = () => {
    editor?.getAction("editor.action.formatDocument")?.run();
  };

  const handleUndo = () => {
    editor?.trigger("", "undo", null);
  };

  const handleRedo = () => {
    editor?.trigger("", "redo", null);
  };

  const handleCopy = async () => {
    const value = editor?.getValue();
    if (value) {
      await navigator.clipboard.writeText(value);
    }
  };

  return (
    <div className="d-flex gap-2 mb-3 flex-wrap">
      <button
        type="button"
        className="btn btn-sm btn-outline-primary"
        onClick={handleFormat}
      >
        Format
      </button>

      <button
        type="button"
        className="btn btn-sm btn-outline-secondary"
        onClick={handleUndo}
      >
        Undo
      </button>

      <button
        type="button"
        className="btn btn-sm btn-outline-secondary"
        onClick={handleRedo}
      >
        Redo
      </button>

      <button
        type="button"
        className="btn btn-sm btn-outline-success"
        onClick={handleCopy}
      >
        Copy
      </button>
    </div>
  );
}

export default Toolbar;

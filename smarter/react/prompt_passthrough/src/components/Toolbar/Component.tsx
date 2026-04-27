// ToolbarButton component for rendering toolbar buttons

interface ToolbarButtonProps {
  onClick: () => void;
  title: string;
  iconClass: string;
}

function ToolbarButton({ onClick, title, iconClass }: ToolbarButtonProps) {
  return (
    <button
      type="button"
      className="btn btn-sm btn-icon btn-light"
      onClick={onClick}
      title={title}
    >
      <i className={iconClass}>
        <span className="path1"></span>
        <span className="path2"></span>
      </i>
    </button>
  );
}
import { useState } from "react";
import type * as monaco from "monaco-editor";

interface ToolbarProps {
  editor: monaco.editor.IStandaloneCodeEditor | null;
}


interface CopyiedMessageProps {
  show_copied: boolean;
}

function CopyiedMessage({ show_copied }: CopyiedMessageProps) {

  const showCopiedMessageStyle: React.CSSProperties = {
            position: "absolute",
            top: "-2.5rem",
            left: 0,
            right: 0,
            margin: "0 auto",
            width: "fit-content",
            background: "#222",
            color: "#fff",
            padding: "0.5rem 1.25rem",
            borderRadius: "0.5rem",
            fontSize: "1rem",
            zIndex: 10,
            boxShadow: "0 2px 8px rgba(0,0,0,0.15)",
            pointerEvents: "none",
            textAlign: "center",
            opacity: 0.95,
            transition: "opacity 0.2s",
          };

   return (
    <>
      {show_copied && (
        <div style={showCopiedMessageStyle}>Copied to clipboard</div>
      )}
    </>
    );

}


function Toolbar({ editor }: ToolbarProps) {
  const [copyIcon, setCopyIcon] = useState("ki-copy");
  const [showCopied, setShowCopied] = useState(false);

  const handleFormat = () => {
    editor?.getAction("editor.action.formatDocument")?.run();
  };

  const handleFileNew = () => {
    editor?.setValue("");
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

      console.log("Copied to clipboard:", value);

      setShowCopied(true);
      setCopyIcon("ki-copy-success");

      setTimeout(() => {
        setShowCopied(false);
        setCopyIcon("ki-copy");
      }, 1000);
    }
  };

  const handleFileOpen = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".json,application/json";

    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];

      if (file) {
        const reader = new FileReader();

        reader.onload = (event) => {
          const text = event.target?.result as string;
          editor?.setValue(text);
        };

        reader.readAsText(file);
      }
    };

    input.click();
  };

  const handleFileSave = () => {
    const value = editor?.getValue();

    if (value) {
      const blob = new Blob([value], {
        type: "application/json",
      });

      const url = URL.createObjectURL(blob);

      const a = document.createElement("a");
      a.href = url;
      a.download = "request.json";
      a.click();

      URL.revokeObjectURL(url);
    }
  };


  return (
    <div className="d-flex gap-2 mb-3 flex-wrap align-items-center position-relative">
      <ToolbarButton
        onClick={handleFileNew}
        title="File New"
        iconClass="ki-duotone ki-document fs-2"
      />
      <ToolbarButton
        onClick={handleFileOpen}
        title="File Open"
        iconClass="ki-duotone ki-folder fs-2"
      />
      <ToolbarButton
        onClick={handleFileSave}
        title="File Save"
        iconClass="ki-duotone ki-disk fs-2"
      />
      <ToolbarButton
        onClick={handleFormat}
        title="Format JSON"
        iconClass="ki-duotone ki-code fs-2"
      />
      <ToolbarButton
        onClick={handleUndo}
        title="Undo"
        iconClass="ki-duotone ki-arrow-circle-left fs-2"
      />
      <ToolbarButton
        onClick={handleRedo}
        title="Redo"
        iconClass="ki-duotone ki-arrow-circle-right fs-2"
      />
      <ToolbarButton
        onClick={handleCopy}
        title="Copy JSON"
        iconClass={`ki-duotone ${copyIcon} fs-2`}
      />
      <CopyiedMessage show_copied={showCopied} />
    </div>
  );
}

export default Toolbar;

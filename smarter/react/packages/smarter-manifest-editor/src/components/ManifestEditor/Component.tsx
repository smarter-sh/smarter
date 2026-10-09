/**
 * ManifestEditor Component
 *
 * A Monaco YAML editor for a Smarter manifest, with a copy button on its top right. It marks the
 * manifest's errors, i.e. its YAML syntax errors, and the errors of its SAM model.
 *
 * It uses the same editor options as @smarter/prompt-passthrough's editor, with a theme
 * that matches the read-only manifest of the Smarter web console: rounded corners,
 * a charcoal background and a white foreground (see .code-sample-body in common-styles.css).
 */
import { useEffect, useState } from "react";
import Editor, { type BeforeMount, type Monaco, type OnMount } from "@monaco-editor/react";
import type * as monaco from "monaco-editor";

import { useCopy } from "@/lib/useCopy";
import { useLockedFields } from "@/lib/useLockedFields";
import type { ManifestError } from "@/lib/validation";

import "@/components/ManifestEditor/styles.css";

const THEME = "smarter-manifest";
const BACKGROUND = "#333333";
const FOREGROUND = "#f1f1f1";
const MIN_HEIGHT = 300;
const PADDING = 15;
const MARKER_OWNER = "smarter-manifest";

/** The editor's height: its content's height, between MIN_HEIGHT and 75% of the window's height. */
function editorHeight(contentHeight: number): number {
  return Math.max(MIN_HEIGHT, Math.min(contentHeight, Math.round(window.innerHeight * 0.75)));
}

const defineTheme: BeforeMount = (monacoInstance) => {
  monacoInstance.editor.defineTheme(THEME, {
    base: "vs-dark",
    inherit: true,
    rules: [{ token: "", foreground: FOREGROUND.slice(1) }],
    colors: {
      "editor.background": BACKGROUND,
      "editor.foreground": FOREGROUND,
      "editorGutter.background": BACKGROUND,
    },
  });
};

interface ManifestEditorProps {
  value: string;
  errors: ManifestError[];
  editor: monaco.editor.IStandaloneCodeEditor | null;
  onEditorDidMount: (editor: monaco.editor.IStandaloneCodeEditor) => void;
  onChange: (value: string) => void;
}

function ManifestEditor({ value, errors, editor, onEditorDidMount, onChange }: ManifestEditorProps) {
  const [height, setHeight] = useState(MIN_HEIGHT);
  const [monacoInstance, setMonacoInstance] = useState<Monaco | null>(null);
  const { copied, copy } = useCopy(editor);
  useLockedFields(editor, monacoInstance);

  // mark each error in the editor, from its position to the end of its line.
  useEffect(() => {
    const model = editor?.getModel();
    if (!model || !monacoInstance) return;
    const markers = errors.map((error) => {
      const position = model.getPositionAt(error.offset);
      return {
        severity: monacoInstance.MarkerSeverity.Error,
        message: error.message,
        source: error.source === "yaml" ? "YAML" : "Smarter manifest",
        startLineNumber: position.lineNumber,
        startColumn: position.column,
        endLineNumber: position.lineNumber,
        endColumn: model.getLineMaxColumn(position.lineNumber),
      };
    });
    monacoInstance.editor.setModelMarkers(model, MARKER_OWNER, markers);
  }, [editor, monacoInstance, errors]);

  const handleMount: OnMount = (editorInstance, monacoFromEditor) => {
    setMonacoInstance(monacoFromEditor);
    setHeight(editorHeight(editorInstance.getContentHeight()));
    editorInstance.onDidContentSizeChange((e) => setHeight(editorHeight(e.contentHeight)));
    onEditorDidMount(editorInstance);
  };

  return (
    <div className="code-sample-body manifest-editor-window">
      <button
        type="button"
        className="btn btn-sm btn-icon manifest-editor-copy"
        title="Copy: Copy this manifest to the clipboard"
        onClick={copy}
      >
        <i className={`ki-duotone ${copied ? "ki-copy-success" : "ki-copy"} fs-2`}>
          <span className="path1"></span>
          <span className="path2"></span>
        </i>
      </button>
      <Editor
        height={`${height}px`}
        defaultLanguage="yaml"
        theme={THEME}
        value={value}
        beforeMount={defineTheme}
        onMount={handleMount}
        onChange={(newValue) => onChange(newValue ?? "")}
        options={{
          minimap: { enabled: false },
          fontSize: 14,
          fontFamily: '"Fira Code", "Consolas", "Monaco", monospace',
          fontLigatures: true,
          lineHeight: 22,
          wordWrap: "on",
          automaticLayout: true,
          scrollBeyondLastLine: false,
          padding: { top: PADDING, bottom: PADDING },
          renderLineHighlight: "none",
          tabSize: 2,
        }}
      />
    </div>
  );
}

export default ManifestEditor;

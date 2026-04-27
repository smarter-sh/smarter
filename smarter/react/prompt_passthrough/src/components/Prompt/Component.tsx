
import { useRef, useState } from "react";
import type * as monaco from "monaco-editor";
import Editor from "@monaco-editor/react";
import Toolbar from "./Toolbar";

function Prompt() {
  const [requestJson, setRequestJson] = useState(
    `{
  "model": "gpt-4o-mini",
  "messages": [
    {
      "role": "user",
      "content": "Hello world"
    }
  ],
  "temperature": 0.7
}`,
  );

  const editorRef = useRef<monaco.editor.IStandaloneCodeEditor | null>(null);

  const handleEditorDidMount = (editor: monaco.editor.IStandaloneCodeEditor) => {
    editorRef.current = editor;
  };

  return (
    <div className="col-lg-6">
      <div className="card shadow-sm">
        <div className="card-header d-flex justify-content-center align-items-center">
          <h3 className="mb-0">Request JSON</h3>
        </div>

        <div className="card-body">
          <Toolbar editor={editorRef.current} />

          <Editor
            height="750px"
            defaultLanguage="json"
            theme="vs-dark"
            value={requestJson}
            onMount={handleEditorDidMount}
            onChange={(value) => setRequestJson(value || "")}
            options={{
              minimap: { enabled: false },
              fontSize: 14,
              fontFamily: '"Fira Code", "Consolas", "Monaco", monospace',
              fontLigatures: true,
              lineHeight: 22,
              wordWrap: "on",
              formatOnPaste: true,
              formatOnType: true,
              automaticLayout: true,
            }}
          />
        </div>
      </div>
    </div>
  );
}

export default Prompt;

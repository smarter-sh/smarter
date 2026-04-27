import { useState } from "react";
import type * as monaco from "monaco-editor";
import Editor from "@monaco-editor/react";
import Toolbar from "../Toolbar/Component";
import LLMProviderSelector from "../LLMProviderSelector";
import TemplateSelector from "../TemplateSelector/Component";
import getTemplateJson from "./templates";
import getApiUrl from "./apis";

import "./styles.css";

function Prompt() {
  const [requestJson, setRequestJson] = useState(getTemplateJson("1", "1"));
  const [editor, setEditor] =
    useState<monaco.editor.IStandaloneCodeEditor | null>(null);
  const [llmProviderId, setLLMProvider] = useState("1");
  const [templateId, setTemplateId] = useState("1");

  const handleEditorDidMount = (
    editorInstance: monaco.editor.IStandaloneCodeEditor,
  ) => {
    setEditor(editorInstance);
  };

  const handleLLMProviderChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setLLMProvider(e.target.value);
    const template = getTemplateJson(templateId, e.target.value);
    setRequestJson(template);
  };
  const handleTemplateChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setTemplateId(e.target.value);
    const template = getTemplateJson(e.target.value, llmProviderId);
    setRequestJson(template);
  };


  return (
    <div className="col-lg-12">
      <div className="card shadow-sm">
        <div className="card-header d-flex justify-content-center align-items-center">
          <h4 className="mt-4 p-4">LLM Request JSON</h4>
          <div className="row w-100 mt-3 mb-2">
            <div className="col-6">
              <LLMProviderSelector
                value={llmProviderId}
                onChange={handleLLMProviderChange}
              />
            </div>
            <div className="col-6">
              <TemplateSelector
                value={templateId}
                onChange={handleTemplateChange}
              />
            </div>
          </div>
          <div className="row w-100 mt-3 mb-2">
            <div className="col-9">
              <input
                type="text"
                className="form-control"
                value={`${getApiUrl(llmProviderId)}/chat/completions`}
                readOnly
                style={{ backgroundColor: "#f8f9fa", fontSize: "0.95rem" }}
              />
            </div>
            <div className="col-3 d-flex align-items-center justify-content-end">
              <button className="btn btn-primary w-100" type="button">
                SEND
              </button>
            </div>
          </div>
        </div>

        <div className="card-body">
          <Toolbar editor={editor} />

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

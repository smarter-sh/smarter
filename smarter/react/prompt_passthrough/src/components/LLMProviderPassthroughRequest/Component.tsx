import React from "react";
import Editor from "@monaco-editor/react";
import type { editor as monaco } from "monaco-editor";
import Toolbar from "@/components/Toolbar";
import LLMProviderSelector from "@/components/LLMProviderSelector";
import TemplateSelector from "@/components/TemplateSelector/";

import { type LLMProvider } from "@/components/LLMProviders";

import "./styles.css";

export interface ProviderPassthroughRequestProps {
  providersJson: LLMProvider[];
  llmProviderId: string;
  templateId: string;
  providerBaseUrl: string;
  isSending: boolean;
  editor: monaco.IStandaloneCodeEditor | null;
  requestJson: string;
  onLLMProviderChange: (e: React.ChangeEvent<HTMLSelectElement>) => void;
  onTemplateChange: (e: React.ChangeEvent<HTMLSelectElement>) => void;
  onSend: () => void;
  onEditorDidMount: (editorInstance: monaco.IStandaloneCodeEditor) => void;
  onRequestJsonChange: (value: string) => void;
}

export default function LLMProviderPassthroughRequest({
  providersJson,
  llmProviderId,
  templateId,
  providerBaseUrl,
  isSending,
  editor,
  requestJson,
  onLLMProviderChange,
  onTemplateChange,
  onSend,
  onEditorDidMount,
  onRequestJsonChange,
}: ProviderPassthroughRequestProps) {
  return (
    <div className="card shadow-sm">
      <div className="card-header d-flex flex-column align-items-stretch">
        <div className="row w-100 mt-3 mb-2">
          <div className="col-6">
            <LLMProviderSelector
              providersJson={providersJson}
              value={llmProviderId}
              onChange={onLLMProviderChange}
            />
          </div>
          <div className="col-6">
            <TemplateSelector value={templateId} onChange={onTemplateChange} />
          </div>
        </div>
        <div className="row w-100 mt-3 mb-2">
          <div className="col-9">
            <input
              type="text"
              className="form-control"
              value={
                providerBaseUrl ? `${providerBaseUrl}chat/completions` : ""
              }
              readOnly
              style={{ backgroundColor: "#f8f9fa", fontSize: "0.95rem" }}
            />
          </div>
          <div className="col-3 d-flex align-items-center justify-content-end">
            <button
              className="btn btn-primary w-100"
              type="button"
              onClick={onSend}
              disabled={isSending}
            >
              {isSending ? "SENDING..." : "SEND"}
            </button>
          </div>
        </div>
      </div>

      <div className="card-body">
        <Toolbar editor={editor} />
        <Editor
          height="500px"
          defaultLanguage="json"
          theme="vs-dark"
          value={requestJson}
          onMount={onEditorDidMount}
          onChange={(value) => onRequestJsonChange(value || "")}
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
  );
}

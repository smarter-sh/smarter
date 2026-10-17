import React from "react";
import Editor from "@monaco-editor/react";
import type { editor as monaco } from "monaco-editor";
import Toolbar from "@/components/Toolbar";
import LLMProviderSelector from "@/components/LLMProviderSelector";
import TemplateSelector from "@/components/TemplateSelector/";

import { type LLMProvider } from "@/components/LLMProviders";

import "@/components/LLMProviderPassthroughRequest/styles.css";
import { gettext } from "@smarter/common";

export interface ProviderPassthroughRequestProps {
  providersJson: LLMProvider[];
  llmProviderId: number;
  connectivityTestPath: string;
  templateId: number;
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
  connectivityTestPath,
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
      <div className="card-header d-block py-5">
        <div className="d-flex flex-wrap gap-4 mb-4">
          <label className="passthrough-request-field">
            <span className="passthrough-request-label">{gettext("LLM provider")}</span>
            <LLMProviderSelector providersJson={providersJson} value={llmProviderId} onChange={onLLMProviderChange} />
          </label>
          <label className="passthrough-request-field">
            <span className="passthrough-request-label">{gettext("Prompt template")}</span>
            <TemplateSelector value={templateId} onChange={onTemplateChange} />
          </label>
        </div>
        <div className="input-group">
          <input
            type="text"
            aria-label={gettext("Endpoint")}
            className="form-control bg-light font-monospace fs-7"
            value={providerBaseUrl ? `${providerBaseUrl}${connectivityTestPath}` : ""}
            readOnly
          />
          <button className="btn btn-primary px-8" type="button" onClick={onSend} disabled={isSending}>
            {isSending ? (
              <span className="spinner-border spinner-border-sm me-2" aria-hidden="true"></span>
            ) : (
              <i className="ki-outline ki-send fs-4 me-1" aria-hidden="true"></i>
            )}
            {isSending ? gettext("SENDING...") : gettext("SEND")}
          </button>
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

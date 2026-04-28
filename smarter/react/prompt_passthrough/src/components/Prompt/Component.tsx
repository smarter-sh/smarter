/**
 * Prompt Component
 *
 * Provides a UI for constructing and sending passthrough API requests
 * to various LLM providers. Features include:
 * - LLM provider and template selection via dropdowns
 * - Display of the resolved target API endpoint
 * - Monaco-based JSON editor for composing request payloads
 * - Editor toolbar for common actions
 * - SEND button that POSTs the request and displays the response
 *
 * CSRF token validation is performed via cookie lookup before each request.
 * The API response is rendered by the Response component below the editor.
 *
 * Dependencies:
 * - @monaco-editor/react — code editor
 * - @/components/Toolbar, LLMProviderSelector, TemplateSelector, Response — UI components
 * - @/lib/cookie, @/lib/django — CSRF and fetch utilities
 * - ./templates, ./llmApis — request template and URL helpers
 */
import { useState } from "react";
import type * as monaco from "monaco-editor";
import Editor from "@monaco-editor/react";
import Toolbar from "@/components/Toolbar";
import LLMProviderSelector from "@/components/LLMProviderSelector";
import TemplateSelector from "@/components/TemplateSelector/";
import Response from "@/components/Response";
import getTemplateJson from "./templates";
import getApiUrl, { getSmarterApiUrlSlug } from "./llmApis";
import getCookie from "@/lib/cookie";
import fetchDjangoUrl from "@/lib/django";

import "./styles.css";

interface PromptProps {
  apiUrl: string;
  csrfCookieName: string;
  csrftoken: string;
  djangoSessionCookieName: string;
  cookieDomain: string;
  defaultLLMProviderId: string | undefined;
  defaultTemplateId: string | undefined;
}

function Prompt({
  apiUrl,
  csrfCookieName,
  csrftoken,
  djangoSessionCookieName,
  cookieDomain,
  defaultLLMProviderId,
  defaultTemplateId,
}: PromptProps) {
  const [requestJson, setRequestJson] = useState(
    getTemplateJson(defaultTemplateId ?? "1", defaultLLMProviderId ?? "1"),
  );
  const [editor, setEditor] =
    useState<monaco.editor.IStandaloneCodeEditor | null>(null);
  const [llmProviderId, setLLMProvider] = useState(defaultLLMProviderId ?? "1");
  const [templateId, setTemplateId] = useState(defaultTemplateId ?? "1");
  const [apiResponse, setApiResponse] = useState<{
    status: number;
    body: any;
  } | null>(null);

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

  const handleSend = async () => {
    console.log("Sending request. apiUrl:", apiUrl);

    const csrftokenFromCookie =
      getCookie(
        {
          name: csrfCookieName,
          expiration: null,
          domain: cookieDomain,
          value: null,
        },
        "",
      ) || "";
    if (csrftokenFromCookie !== csrftoken) {
      console.warn(
        "CSRF token mismatch. Cookie value:",
        csrftokenFromCookie,
        "Expected value:",
        csrftoken,
      );
    }
    const providerSlug = getSmarterApiUrlSlug(llmProviderId);
    const url = new URL(providerSlug + "/", apiUrl).toString();
    const res = await fetchDjangoUrl(
      requestJson,
      url,
      csrftoken,
      djangoSessionCookieName,
      csrfCookieName,
      cookieDomain,
    );
    const data = await res.json();

    console.log("API Response Status:", res.status);
    console.log("API Response Data:", data);

    setApiResponse({ status: res.status, body: data });
  };

  return (
    <>
      <div className="row d-flex mb-3">
        <div className="col-lg-12">
          <div className="card shadow-sm">
            <div className="card-header d-flex justify-content-center align-items-center">
              <h4 className="mt-4 p-4">LLM Provider API Passthrough Request</h4>
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
                  <button
                    className="btn btn-primary w-100"
                    type="button"
                    onClick={handleSend}
                  >
                    SEND
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
      </div>
      <div className="row d-flex">
        <div className="col-lg-12">
          <Response apiResponse={apiResponse} />
        </div>
      </div>
    </>
  );
}

export default Prompt;

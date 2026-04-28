/**
 * Prompt Component
 *
 * This component provides a user interface for constructing and sending passthrough API requests
 * to various LLM (Large Language Model) providers. It features:
 * - Provider and template selection via dropdowns
 * - Dynamic display of the target API endpoint
 * - Monaco-based JSON editor for request payloads
 * - Toolbar for editor actions
 * - "SEND" button (UI only; sending logic not included here)
 *
 * State is managed for the selected provider, template, editor instance, and request JSON.
 * The component is styled using Bootstrap classes and custom CSS.
 *
 * Dependencies:
 * - @monaco-editor/react for the code editor
 * - Toolbar, LLMProviderSelector, TemplateSelector (local components)
 * - getTemplateJson, getApiUrl (utility functions)
 */
import { useState } from "react";
import type * as monaco from "monaco-editor";
import Editor from "@monaco-editor/react";
import Toolbar from "../Toolbar/Component";
import LLMProviderSelector from "../LLMProviderSelector";
import TemplateSelector from "../TemplateSelector/Component";
import Response from "../Response";
import getTemplateJson from "./templates";
import getApiUrl, {getSmarterApiUrlSlug} from "./llmApis";
import { getCookie } from "./cookie";

import "./styles.css";


function Prompt({ apiUrl, csrfCookieName, csrftoken, djangoSessionCookieName, cookieDomain, defaultLLMProviderId, defaultTemplateId }: { apiUrl: string; csrfCookieName: string; csrftoken: string; djangoSessionCookieName: string; cookieDomain: string; defaultLLMProviderId: string | undefined; defaultTemplateId: string | undefined }) {
  const [requestJson, setRequestJson] = useState(getTemplateJson(defaultTemplateId ?? "1", defaultLLMProviderId ?? "1"));
  const [editor, setEditor] =
    useState<monaco.editor.IStandaloneCodeEditor | null>(null);
  const [llmProviderId, setLLMProvider] = useState(defaultLLMProviderId ?? "1");
  const [templateId, setTemplateId] = useState(defaultTemplateId ?? "1");
  const [apiResponse, setApiResponse] = useState<{ status: number; body: any } | null>(null);

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

    const userAgent = "SmarterChat/1.0";
    const applicationJson = "application/json";
    const authToken = getCookie({ name: djangoSessionCookieName, expiration: null, domain: cookieDomain, value: null }, "") || "";
    const csrftokenFromCookie = getCookie({ name: csrfCookieName, expiration: null, domain: cookieDomain, value: null }, "") || "";
    if (csrftokenFromCookie !== csrftoken) {
        console.warn("CSRF token mismatch. Cookie value:", csrftokenFromCookie, "Expected value:", csrftoken);
    }
    const requestHeaders = {
      Accept: applicationJson,
      "Content-Type": applicationJson,
      "X-CSRFToken": csrftoken,
      Origin: window.location.origin,
      // Cookie: requestCookies,
      Authorization: `Bearer ${authToken}`,
      "User-Agent": userAgent,
    };


    const providerSlug = getSmarterApiUrlSlug(llmProviderId);
    const url = new URL(providerSlug + "/", apiUrl).toString();

    console.log("API URL:", url);
    console.log("Request JSON:", requestJson);

    const res = await fetch(url, {
      method: "POST",
      headers: requestHeaders,
      body: requestJson,
    });

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
                  <button className="btn btn-primary w-100" type="button" onClick={handleSend}>
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

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
import { useEffect, useState } from "react";
import type * as monaco from "monaco-editor";
import Editor from "@monaco-editor/react";
import Toolbar from "@/components/Toolbar";
import LLMProviders, { type LLMProvider } from "@/components/LLMProviders";
import LLMProviderSelector from "@/components/LLMProviderSelector";
import TemplateSelector from "@/components/TemplateSelector/";
import Response from "@/components/Response";
import getPromptTemplate from "./templates";

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
  providerApiUrl: string;
}

function Prompt({
  apiUrl,
  csrfCookieName,
  csrftoken,
  djangoSessionCookieName,
  cookieDomain,
  defaultLLMProviderId,
  defaultTemplateId,
  providerApiUrl,
}: PromptProps) {

  // UI state
  const [editor, setEditor] =
    useState<monaco.editor.IStandaloneCodeEditor | null>(null);
  const [isSending, setIsSending] = useState(false);
  const [apiResponse, setApiResponse] = useState<{
    status: number;
    body: any;
  } | null>(null);

  // LLM provider and template state
  const [providersJson, setProviders] = useState<LLMProvider[]>([]);
  const [templateId, setTemplateId] = useState(defaultTemplateId ?? "1");
  const [llmProviderId, setLLMProvider] = useState(defaultLLMProviderId ?? "1");

  // Derived state, from llmProviderId
  const [defaultModel, setDefaultModel] = useState("");
  const [providerBaseUrl, setProviderBaseUrl] = useState("");
  const [providerSlug, setProviderSlug] = useState("");

  // Final request JSON state (function of providersJson, llmProviderId, templateId, defaultModel)
  const [requestJson, setRequestJson] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    LLMProviders(providerApiUrl, controller.signal)
      .then((providers) => {

        // set the provider list, and identify the default provider based on
        // the "isDefault" flag (or fallback to first provider if none
        // marked as default).
        setProviders(providers);
        const default_provider = providers.filter(
          (p) => Boolean(p.isDefault) === true,
        )[0] || providers[0];
        if (!default_provider) {
          console.warn("No LLM providers found from API");
          return;
        }

        // initialize all state that depends on the provider list
        // and default provider.
        setDefaultModel(default_provider.defaultModel);
        setLLMProvider(default_provider.id.toString());

        // lastly, generate the initial request JSON based on the default
        // provider and template.
        const templateJson = getPromptTemplate(
          templateId,
          default_provider.defaultModel,
        );
        setRequestJson(templateJson);
      })
      .catch((err: Error) => {
        if (err.name !== "AbortError") {
          console.error("Error fetching LLM providers:", err);
        }
      });
    return () => controller.abort();
  }, [providerApiUrl]);

  useEffect(() => {
    const provider = providersJson.find((p) => String(p.id) === llmProviderId);
    if (provider) {
      setProviderBaseUrl(provider.baseUrl);
      setProviderSlug(provider.rfc1034CompliantName);
      setDefaultModel(provider.defaultModel);
    }
  }, [providersJson, llmProviderId]);

  const handleEditorDidMount = (
    editorInstance: monaco.editor.IStandaloneCodeEditor,
  ) => {
    setEditor(editorInstance);
  };
  const handleLLMProviderChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newId = e.target.value;
    setLLMProvider(newId);
    const provider = providersJson.find((p) => String(p.id) === newId);
    if (provider) {
      setProviderBaseUrl(provider.baseUrl);
      setProviderSlug(provider.rfc1034CompliantName);
      setDefaultModel(provider.defaultModel);
      const templateJson = getPromptTemplate(
        templateId,
        provider.defaultModel,
      );
      setRequestJson(templateJson);
    }
  };
  const handleTemplateChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setTemplateId(e.target.value);
    const templateJson = getPromptTemplate(
      e.target.value,
      defaultModel ?? "",
    );
    setRequestJson(templateJson);
  };

  const handleSend = async () => {
    if (isSending) {
      return;
    }

    setIsSending(true);
    try {
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

      setApiResponse({ status: res.status, body: data });
    } finally {
      setIsSending(false);
    }
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
                    providersJson={providersJson}
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
                    value={
                      providerBaseUrl
                        ? `${providerBaseUrl}/chat/completions`
                        : ""
                    }
                    readOnly
                    style={{ backgroundColor: "#f8f9fa", fontSize: "0.95rem" }}
                  />
                </div>
                <div className="col-3 d-flex align-items-center justify-content-end">
                  <button
                    className="btn btn-primary w-100"
                    type="button"
                    onClick={handleSend}
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
          <Response apiResponse={apiResponse} isProcessing={isSending} />
        </div>
      </div>
    </>
  );
}

export default Prompt;

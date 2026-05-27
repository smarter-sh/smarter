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

import { loggerPrefix } from "@/const";
import getPromptTemplate from "./templates";
import LLMProviderMetaData from "@/components/LLMProviderMetaData";
import LLMProviders, { type LLMProvider } from "@/components/LLMProviders";
import LLMProviderPassthroughResponse from "@/components/LLMProviderPassthroughResponse";
import LLMProviderPassthroughRequest from "@/components/LLMProviderPassthroughRequest";

import fetchDjangoUrl from "@/lib/django";

import "./styles.css";

interface PromptProps {
  apiUrl: string;
  csrfCookieName: string;
  djangoSessionCookieName: string;
  cookieDomain: string;
  defaultLLMProviderId: string;
  defaultTemplateId: string;
  providerApiUrl: string;
}

function Prompt({
  apiUrl,
  csrfCookieName,
  djangoSessionCookieName,
  cookieDomain,
  defaultLLMProviderId,
  defaultTemplateId,
  providerApiUrl,
}: PromptProps) {
  // UI state
  const [editor, setEditor] = useState<monaco.editor.IStandaloneCodeEditor | null>(null);
  const [isSending, setIsSending] = useState(false);
  const [apiResponse, setApiResponse] = useState<{
    status: number;
    body: any;
  } | null>(null);

  // LLM provider and template state
  const [providersJson, setProviders] = useState<LLMProvider[]>([]);
  const [selectedProviderJson, setSelectedProviderJson] = useState<LLMProvider | null>(null);
  const [templateId, setTemplateId] = useState(defaultTemplateId ?? "1");
  const [llmProviderId, setLLMProvider] = useState(defaultLLMProviderId ?? "1");

  // Derived state, from llmProviderId
  const [defaultModel, setDefaultModel] = useState("");
  const [providerBaseUrl, setProviderBaseUrl] = useState("");
  const [providerSlug, setProviderSlug] = useState("");
  const [connectivityTestPath, setConnectivityTestPath] = useState("");

  // Final request JSON state (function of providersJson, llmProviderId, templateId, defaultModel)
  const [requestJson, setRequestJson] = useState("");
  const [activeTab, setActiveTab] = useState<"request" | "response">("request");

  useEffect(() => {
    const controller = new AbortController();
    LLMProviders(providerApiUrl, controller.signal)
      .then((providers) => {
        // set the provider list, and identify the default provider based on
        // the "isDefault" flag (or fallback to first provider if none
        // marked as default).
        setProviders(providers);
        const default_provider = providers.filter((p) => Boolean(p.isDefault) === true)[0] || providers[0];
        setSelectedProviderJson(default_provider);
        if (!default_provider) {
          console.warn(loggerPrefix, "No LLM providers found from API");
          return;
        }

        // initialize all state that depends on the provider list
        // and default provider.
        setDefaultModel(default_provider.defaultModel);
        setLLMProvider(default_provider.id.toString());

        // lastly, generate the initial request JSON based on the default
        // provider and template.
        const templateJson = getPromptTemplate(templateId, default_provider.defaultModel);
        setRequestJson(templateJson);
      })
      .catch((err: Error) => {
        if (err.name !== "AbortError") {
          console.error(loggerPrefix, "Error fetching LLM providers:", err);
        }
      });
    return () => controller.abort();
  }, [providerApiUrl]);

  useEffect(() => {
    const provider = providersJson.find((p) => String(p.id) === llmProviderId);
    if (provider) {
      setSelectedProviderJson(provider);
      setProviderBaseUrl(provider.baseUrl);
      setProviderSlug(provider.rfc1034CompliantName);
      setConnectivityTestPath(provider.connectivityTestPath);
      setDefaultModel(provider.defaultModel);
    }
  }, [providersJson, llmProviderId]);

  const handleEditorDidMount = (editorInstance: monaco.editor.IStandaloneCodeEditor) => {
    setEditor(editorInstance);
  };
  const handleLLMProviderChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newId = e.target.value;
    setLLMProvider(newId);
    const provider = providersJson.find((p) => String(p.id) === newId);
    if (provider) {
      setSelectedProviderJson(provider);
      setProviderBaseUrl(provider.baseUrl);
      setProviderSlug(provider.rfc1034CompliantName);
      setConnectivityTestPath(provider.connectivityTestPath);
      setDefaultModel(provider.defaultModel);
      const templateJson = getPromptTemplate(templateId, provider.defaultModel);
      setRequestJson(templateJson);
    }
  };
  const handleTemplateChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setTemplateId(e.target.value);
    const templateJson = getPromptTemplate(e.target.value, defaultModel ?? "");
    setRequestJson(templateJson);
  };

  const handleSend = async () => {
    if (isSending) {
      return;
    }

    setIsSending(true);
    try {
      const url = new URL(providerSlug + "/", apiUrl).toString();
      const res = await fetchDjangoUrl(
        requestJson,
        url,
        djangoSessionCookieName,
        csrfCookieName,
        cookieDomain,
      );
      const data = await res.json();
      console.debug(loggerPrefix, `fetched response from ${url}:`, data);

      setApiResponse({ status: res.status, body: data });
      setActiveTab("response");
    } finally {
      setIsSending(false);
    }
  };

  return (
    <>
      <div className="row d-flex mb-3">
        <div className="col-lg-12">
          <h3 className="mt-4 p-4">LLM Provider API Passthrough</h3>
          <ul className="nav nav-tabs" role="tablist">
            <li className="nav-item" role="presentation">
              <button
                className={`nav-link ${activeTab === "request" ? "active" : ""}`}
                type="button"
                onClick={() => setActiveTab("request")}
                role="tab"
                aria-selected={activeTab === "request"}
              >
                Request
              </button>
            </li>
            <li className="nav-item" role="presentation">
              <button
                className={`nav-link ${activeTab === "response" ? "active" : ""}`}
                type="button"
                onClick={() => setActiveTab("response")}
                role="tab"
                aria-selected={activeTab === "response"}
              >
                Response
              </button>
            </li>
          </ul>

          {activeTab === "request" && (
            <LLMProviderPassthroughRequest
              providersJson={providersJson}
              llmProviderId={llmProviderId}
              connectivityTestPath={connectivityTestPath}
              templateId={templateId}
              providerBaseUrl={providerBaseUrl}
              isSending={isSending}
              editor={editor}
              requestJson={requestJson}
              onLLMProviderChange={handleLLMProviderChange}
              onTemplateChange={handleTemplateChange}
              onSend={handleSend}
              onEditorDidMount={handleEditorDidMount}
              onRequestJsonChange={setRequestJson}
            />
          )}

          {activeTab === "response" && (
            <LLMProviderPassthroughResponse apiResponse={apiResponse} isProcessing={isSending} />
          )}
        </div>
        {activeTab === "request" && <LLMProviderMetaData provider={selectedProviderJson} />}
      </div>
    </>
  );
}

export default Prompt;

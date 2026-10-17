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
import { useEffect, useEffectEvent, useState } from "react";
import type * as monaco from "monaco-editor";

import { fetchDjangoUrl, gettext } from "@smarter/common";
import type { SessionContext } from "@smarter/common";

import { loggerPrefix } from "@/const";
import getPromptTemplate from "@/components/Prompt/templates";
import LLMProviderMetaData from "@/components/LLMProviderMetaData";
import LLMProviders, { type LLMProvider } from "@/components/LLMProviders";
import LLMProviderPassthroughResponse from "@/components/LLMProviderPassthroughResponse";
import type { PassthroughResponse } from "@/components/LLMProviderPassthroughResponse/summary";
import LLMProviderPassthroughRequest from "@/components/LLMProviderPassthroughRequest";

import "@/components/Prompt/styles.css";

interface PromptProps {
  sessionContext: SessionContext;
  defaultLLMProviderId: number;
  defaultTemplateId: number;
  providerApiUrl: string;
}

function Prompt({ sessionContext, defaultLLMProviderId, defaultTemplateId, providerApiUrl }: PromptProps) {
  // UI state
  const [editor, setEditor] = useState<monaco.editor.IStandaloneCodeEditor | null>(null);
  const [isSending, setIsSending] = useState(false);
  const [apiResponse, setApiResponse] = useState<PassthroughResponse | null>(null);

  // LLM provider and template state
  const [providersJson, setProviders] = useState<LLMProvider[]>([]);
  const [templateId, setTemplateId] = useState(defaultTemplateId ?? 1);
  const [llmProviderId, setLLMProvider] = useState(defaultLLMProviderId ?? 1);

  // Derived from providersJson and llmProviderId, during render.
  const selectedProviderJson = providersJson.find((p) => p.id === llmProviderId) ?? null;
  const defaultModel = selectedProviderJson?.defaultModel ?? "";
  const providerBaseUrl = selectedProviderJson?.baseUrl ?? "";
  const providerSlug = selectedProviderJson?.rfc1034CompliantName ?? "";
  const connectivityTestPath = selectedProviderJson?.connectivityTestPath ?? "";

  // Final request JSON state (function of providersJson, llmProviderId, templateId, defaultModel)
  const [requestJson, setRequestJson] = useState("");
  const [activeTab, setActiveTab] = useState<"request" | "response">("request");

  // when the providers arrive: select the default one, and generate the initial request JSON
  // from it and the current template. An effect event, so that it reads the current templateId
  // without the providers being fetched again whenever the template changes.
  const onProvidersLoaded = useEffectEvent((providers: LLMProvider[]) => {
    // set the provider list, and identify the default provider based on
    // the "isDefault" flag (or fallback to first provider if none
    // marked as default).
    console.debug(loggerPrefix, "Fetched LLM providers from API:", providers);
    setProviders(providers);
    const default_provider = providers.filter((p) => Boolean(p.isDefault) === true)[0] || providers[0];
    if (!default_provider) {
      console.warn(loggerPrefix, "No LLM providers found from API");
      return;
    }
    // selecting the default provider also selects its model, base URL, etc.: see the derived values above.
    setLLMProvider(default_provider.id);
    const templateJson = getPromptTemplate(templateId, default_provider.defaultModel ?? "");
    setRequestJson(templateJson);
  });

  useEffect(() => {
    const controller = new AbortController();
    LLMProviders(providerApiUrl, controller.signal)
      .then((providers) => onProvidersLoaded(providers))
      .catch((err: Error) => {
        if (err.name !== "AbortError") {
          console.error(loggerPrefix, "Error fetching LLM providers:", err);
        }
      });
    return () => controller.abort();
  }, [providerApiUrl]);

  const handleEditorDidMount = (editorInstance: monaco.editor.IStandaloneCodeEditor) => {
    setEditor(editorInstance);
  };
  const handleLLMProviderChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newId = parseInt(e.target.value, 10);
    setLLMProvider(newId);
    const provider = providersJson.find((p) => p.id === newId);
    if (provider) {
      const templateJson = getPromptTemplate(templateId, provider.defaultModel ?? "");
      setRequestJson(templateJson);
    }
  };
  const handleTemplateChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newTemplateId = parseInt(e.target.value, 10);
    setTemplateId(newTemplateId);
    const templateJson = getPromptTemplate(newTemplateId, defaultModel ?? "");
    setRequestJson(templateJson);
  };

  const handleSend = async () => {
    if (isSending) {
      return;
    }

    setIsSending(true);
    // the response tab shows that the request is on its way.
    setActiveTab("response");
    const started = performance.now();
    try {
      // ApiUrl is absolute when Django renders the page, and relative in the Vite dev server's index.html.
      const url = new URL(providerSlug + "/", new URL(sessionContext.ApiUrl, window.location.href)).toString();
      const res = await fetchDjangoUrl(sessionContext, url, requestJson);
      const text = await res.text();
      // a body that isn't JSON, such as a proxy's HTML error page, is shown as it is.
      let body: unknown = text;
      try {
        body = JSON.parse(text);
      } catch {
        console.warn(loggerPrefix, `the response from ${url} isn't JSON`);
      }
      console.debug(loggerPrefix, `fetched response from ${url}:`, body);
      setApiResponse({
        status: res.status,
        statusText: res.statusText,
        body,
        elapsedMs: performance.now() - started,
        size: new Blob([text]).size,
      });
    } catch (err) {
      console.error(loggerPrefix, "Error sending the request:", err);
      const message = err instanceof Error ? err.message : String(err);
      setApiResponse({
        status: 0,
        statusText: "",
        body: { error: { message } },
        elapsedMs: performance.now() - started,
        size: 0,
      });
    } finally {
      setIsSending(false);
    }
  };

  return (
    <>
      <div className="row d-flex mb-3">
        <div className="col-lg-12">
          <h3 className="mt-4 p-4">{gettext("LLM Provider API Passthrough")}</h3>
          <ul className="nav nav-tabs" role="tablist">
            <li className="nav-item" role="presentation">
              <button
                className={`nav-link ${activeTab === "request" ? "active" : ""}`}
                type="button"
                onClick={() => setActiveTab("request")}
                role="tab"
                aria-selected={activeTab === "request"}
              >
                {gettext("Request")}
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
                {gettext("Response")}
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

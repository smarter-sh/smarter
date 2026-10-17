/**
 * Response Component
 *
 * Shows the provider's response to a passthrough request. The header has the HTTP status, as a green
 * or red badge, how long the request took and how big the response was, and buttons to copy or
 * download its JSON. The body starts with a summary: the assistant's reply, with its model, finish
 * reason and token counts, or the error, with its stack trace folded away. The raw JSON follows, in a
 * read-only editor like the request's. Before the first request, the body says how to get a response,
 * and while a request is on its way, a spinner says so.
 *
 * :param apiResponse: The last response, or null before the first.
 * :type apiResponse: PassthroughResponse | null
 * :param isProcessing: True while a request is on its way.
 * :type isProcessing: bool
 */
import { useEffect, useState } from "react";
import Editor from "@monaco-editor/react";

import { gettext } from "@smarter/common";

import { loggerPrefix } from "@/const";
import { CompletionPanel, ErrorPanel } from "@/components/LLMProviderPassthroughResponse/ResponseSummary";
import SuccessEmoji from "@/components/LLMProviderPassthroughResponse/status_success";
import FailureEmoji from "@/components/LLMProviderPassthroughResponse/status_failure";
import {
  completionSummary,
  editorHeight,
  errorSummary,
  formatBytes,
  formatDuration,
  type PassthroughResponse,
} from "@/components/LLMProviderPassthroughResponse/summary";

import "@/components/LLMProviderPassthroughResponse/styles.css";

interface ResponseProps {
  apiResponse: PassthroughResponse | null;
  isProcessing?: boolean;
}

const isSuccess = (status: number) => status >= 200 && status < 300;

function StatusBadge({ response }: { response: PassthroughResponse }) {
  const color = isSuccess(response.status) ? "success" : "danger";
  const label =
    response.status === 0
      ? gettext("Network error")
      : `${response.status}${response.statusText ? ` ${response.statusText}` : ""}`;
  return (
    <span className={`badge badge-light-${color} fs-7 fw-bold px-3 py-2 text-nowrap`}>
      <span className={`bullet bullet-dot bg-${color} h-6px w-6px me-2`}></span>
      {label}
    </span>
  );
}

/** Copy and download buttons for the response's JSON. */
function ResponseActions({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!copied) return;
    const timer = setTimeout(() => setCopied(false), 1500);
    return () => clearTimeout(timer);
  }, [copied]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
    } catch (err) {
      console.error(loggerPrefix, "Couldn't copy the response:", err);
    }
  };

  const handleDownload = () => {
    const url = URL.createObjectURL(new Blob([text], { type: "application/json" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = "response.json";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <>
      <button
        type="button"
        className="btn btn-sm btn-icon btn-light btn-active-light-primary"
        title={copied ? gettext("Copied to clipboard") : gettext("Copy JSON")}
        aria-label={copied ? gettext("Copied to clipboard") : gettext("Copy JSON")}
        onClick={handleCopy}
      >
        <i className={`ki-outline ${copied ? "ki-check text-success" : "ki-copy"} fs-4`}></i>
      </button>
      <button
        type="button"
        className="btn btn-sm btn-icon btn-light btn-active-light-primary"
        title={gettext("Download")}
        aria-label={gettext("Download")}
        onClick={handleDownload}
      >
        <i className="ki-outline ki-file-down fs-4"></i>
      </button>
    </>
  );
}

function Placeholder({ busy }: { busy: boolean }) {
  return (
    <div className="passthrough-response-placeholder" role="status">
      {busy ? (
        <>
          <span className="spinner-border text-primary mb-4" aria-hidden="true"></span>
          <span className="fw-bold text-gray-800">{gettext("Waiting for the provider's response…")}</span>
        </>
      ) : (
        <>
          <span className="passthrough-response-placeholder-icon">
            <i className="ki-outline ki-send fs-1" aria-hidden="true"></i>
          </span>
          <span className="fw-bold text-gray-800">{gettext("No response yet")}</span>
          <span className="text-gray-500 fs-7 mt-1">
            {gettext("Send a request, and the provider's response will appear here.")}
          </span>
        </>
      )}
    </div>
  );
}

function LLMProviderPassthroughResponse({ apiResponse, isProcessing = false }: ResponseProps) {
  const response = isProcessing ? null : apiResponse;
  const isText = typeof response?.body === "string";
  const text = response ? (isText ? (response.body as string) : JSON.stringify(response.body, null, 2)) : "";
  const ok = response ? isSuccess(response.status) : false;
  const completion = response && ok ? completionSummary(response.body) : null;
  // a body that isn't JSON, such as a proxy's HTML error page, can't say what went wrong. The editor shows it.
  const error =
    response && !ok
      ? isText
        ? {
            errorClass: null,
            message: gettext("The response isn't JSON. It's shown below, as it is."),
            stacktrace: null,
          }
        : errorSummary(response.body)
      : null;

  return (
    <div className="col-lg-12">
      <div className="card shadow-sm">
        <div className="card-header passthrough-response-header flex-wrap align-items-center gap-3 py-3">
          <div className="d-flex align-items-center gap-3">
            <h3 className="fw-bold text-gray-900 fs-4 m-0">{gettext("Response")}</h3>
            {response && <StatusBadge response={response} />}
            {response && (ok ? <SuccessEmoji /> : <FailureEmoji />)}
          </div>
          {response && (
            <div className="d-flex align-items-center gap-2 ms-auto">
              <span className="passthrough-response-meta" title={gettext("Time to respond")}>
                <i className="ki-outline ki-timer fs-6 me-1" aria-hidden="true"></i>
                {formatDuration(response.elapsedMs)}
              </span>
              <span className="passthrough-response-meta me-2" title={gettext("Response size")}>
                {formatBytes(response.size)}
              </span>
              <ResponseActions text={text} />
            </div>
          )}
        </div>
        <div className="card-body">
          {!response && <Placeholder busy={isProcessing} />}
          {completion && <CompletionPanel completion={completion} />}
          {error && <ErrorPanel error={error} />}
          {response && (
            <section aria-label={isText ? gettext("Raw response") : gettext("Raw JSON")}>
              <h4 className="passthrough-response-label mb-3">
                <i className="ki-outline ki-code fs-6 me-2" aria-hidden="true"></i>
                {isText ? gettext("Raw response") : gettext("Raw JSON")}
              </h4>
              <Editor
                height={`${editorHeight(text)}px`}
                language={isText ? "plaintext" : "json"}
                theme="vs-dark"
                value={text}
                options={{
                  ariaLabel: gettext("Response JSON"),
                  readOnly: true,
                  domReadOnly: true,
                  minimap: { enabled: false },
                  fontSize: 14,
                  fontFamily: '"Fira Code", "Consolas", "Monaco", monospace',
                  fontLigatures: true,
                  lineHeight: 22,
                  wordWrap: "on",
                  folding: true,
                  scrollBeyondLastLine: false,
                  automaticLayout: true,
                }}
              />
            </section>
          )}
        </div>
      </div>
    </div>
  );
}

export default LLMProviderPassthroughResponse;

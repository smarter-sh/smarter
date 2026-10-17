import { gettext, interpolate } from "@smarter/common";

import type { CompletionSummary, ErrorSummary } from "@/components/LLMProviderPassthroughResponse/summary";

/** The assistant's reply: its text, the tools it called, and the model, finish reason and token counts. */
export function CompletionPanel({ completion }: { completion: CompletionSummary }) {
  const { content, toolCalls, model, finishReason, usage } = completion;
  return (
    <section className="passthrough-response-panel" aria-label={gettext("Reply")}>
      <h4 className="passthrough-response-label">
        <i className="ki-outline ki-message-text fs-6 me-2" aria-hidden="true"></i>
        {gettext("Reply")}
      </h4>
      {content && <p className="passthrough-response-content">{content}</p>}
      {toolCalls.length > 0 && (
        <ul className="passthrough-response-tool-calls" aria-label={gettext("Tool calls")}>
          {toolCalls.map((call, index) => (
            <li key={index}>
              <i className="ki-outline ki-wrench fs-6 me-2" aria-hidden="true"></i>
              <code className="passthrough-response-code">
                {call.name}({call.arguments})
              </code>
            </li>
          ))}
        </ul>
      )}
      {!content && toolCalls.length === 0 && (
        <p className="passthrough-response-content text-gray-500">{gettext("The reply is empty.")}</p>
      )}
      <dl className="passthrough-response-stats">
        {model && (
          <div>
            <dt>{gettext("Model")}</dt>
            <dd>{model}</dd>
          </div>
        )}
        {finishReason && (
          <div>
            <dt>{gettext("Finish reason")}</dt>
            <dd>{finishReason}</dd>
          </div>
        )}
        {usage && (
          <div>
            <dt>{gettext("Tokens")}</dt>
            <dd>
              {/* Translators: token counts of a prompt, e.g. "13 prompt · 7 completion · 20 total". */}
              {interpolate(gettext("%(prompt)s prompt · %(completion)s completion · %(total)s total"), {
                prompt: usage.prompt,
                completion: usage.completion,
                total: usage.total,
              })}
            </dd>
          </div>
        )}
      </dl>
    </section>
  );
}

/** What went wrong: the exception's class and message, and its stack trace, folded, when the api sends one. */
export function ErrorPanel({ error }: { error: ErrorSummary }) {
  return (
    <section className="passthrough-response-panel passthrough-response-error" role="alert">
      <h4 className="passthrough-response-label">
        <i className="ki-outline ki-information fs-6 me-2" aria-hidden="true"></i>
        {gettext("Error")}
        {error.errorClass && <span className="passthrough-response-error-class">{error.errorClass}</span>}
      </h4>
      <p className="passthrough-response-content">{error.message}</p>
      {error.stacktrace && (
        <details className="passthrough-response-stacktrace">
          <summary>{gettext("Stack trace")}</summary>
          <pre>{error.stacktrace}</pre>
        </details>
      )}
    </section>
  );
}

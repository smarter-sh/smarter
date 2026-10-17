/**
 * Reads the parts of a passthrough response worth showing above its raw JSON: the reply of a chat
 * completion, or the message of an error. See smarter.apps.prompt.api.v1.views.passthrough: a
 * success is the provider's ChatCompletion, in OpenAI's shape, and a failure is Smarter's journaled
 * error, {"error": {"errorClass", "description", "stacktrace", ...}}, or {"error", "message"} when
 * the budget is exceeded. Anything else gets no summary, and shows as raw JSON only.
 */

/** The response that Prompt received, and how long it took. */
export interface PassthroughResponse {
  /** The HTTP status, or 0 when no response arrived. */
  status: number;
  statusText: string;
  /** The parsed JSON body, or the body's text when it isn't JSON. */
  body: unknown;
  elapsedMs: number;
  /** The body's size in bytes. */
  size: number;
}

export interface ToolCallSummary {
  name: string;
  arguments: string;
}

export interface TokenUsage {
  prompt: number;
  completion: number;
  total: number;
}

export interface CompletionSummary {
  content: string | null;
  toolCalls: ToolCallSummary[];
  model: string | null;
  finishReason: string | null;
  usage: TokenUsage | null;
}

export interface ErrorSummary {
  /** The exception's class, e.g. NotFoundError, when the api names one. */
  errorClass: string | null;
  message: string;
  stacktrace: string | null;
}

type JsonObject = Record<string, unknown>;

const isObject = (value: unknown): value is JsonObject =>
  typeof value === "object" && value !== null && !Array.isArray(value);

const str = (value: unknown): string | null => (typeof value === "string" && value !== "" ? value : null);

const num = (value: unknown): number => (typeof value === "number" ? value : 0);

/** The first choice of a chat completion, or null when the body isn't one. */
export function completionSummary(body: unknown): CompletionSummary | null {
  if (!isObject(body) || !Array.isArray(body.choices) || !isObject(body.choices[0])) {
    return null;
  }
  const choice = body.choices[0];
  const message = isObject(choice.message) ? choice.message : {};
  const toolCalls = (Array.isArray(message.tool_calls) ? message.tool_calls : []).filter(isObject).map((call) => {
    const fn = isObject(call.function) ? call.function : {};
    return { name: str(fn.name) ?? "?", arguments: typeof fn.arguments === "string" ? fn.arguments : "" };
  });
  const usage = isObject(body.usage)
    ? {
        prompt: num(body.usage.prompt_tokens),
        completion: num(body.usage.completion_tokens),
        total: num(body.usage.total_tokens),
      }
    : null;
  return {
    content: str(message.content),
    toolCalls,
    model: str(body.model),
    finishReason: str(choice.finish_reason),
    usage,
  };
}

/** The error that a failed response describes, or null when it doesn't describe one. */
export function errorSummary(body: unknown): ErrorSummary | null {
  if (!isObject(body)) {
    return null;
  }
  const error = body.error;
  if (isObject(error)) {
    const message = str(error.description) ?? str(error.message) ?? str(body.message);
    if (!message) return null;
    return { errorClass: str(error.errorClass), message, stacktrace: str(error.stacktrace) };
  }
  const message = str(body.message) ?? str(error) ?? str(body.detail);
  return message ? { errorClass: null, message, stacktrace: null } : null;
}

/** The editor's height for a text: its lines at 22px each, from 120px to 600px. */
export function editorHeight(text: string): number {
  const lines = text.split("\n").length;
  return Math.min(600, Math.max(120, lines * 22 + 24));
}

/** A size in bytes, as "846 B", "2.1 KB" or "1.3 MB". */
export function formatBytes(size: number): string {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

/** A duration, as "840 ms" or "1.24 s". */
export function formatDuration(ms: number): string {
  return ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(2)} s`;
}

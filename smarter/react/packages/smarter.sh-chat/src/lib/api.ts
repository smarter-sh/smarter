/**
 * The Smarter api calls of Smarter Chat: the LLMClient's configuration, and its prompts.
 *
 * Both are POSTs, with Django's CSRF token, and with the browser's cookies, so that the Smarter web
 * console's session authenticates them. Each response wraps its payload in "data". See:
 *
 * - smarter.apps.prompt.views.detailviews.prompt_config_view.PromptConfigView: <apiUrl>config/
 * - smarter.apps.llmclient.api.v1.views.base: the LLMClient's prompt api, llmclient.url_llmclient.
 *
 * The contract is versioned (see smarter.apps.prompt.contract). Smarter Chat asks for version 2 with
 * "X-Smarter-Capabilities: chat-contract-v2", and reads version 1 from older platforms, which ignore
 * the header:
 *
 * - version 2: the configuration's LLMClient is "llmclient", and a prompt's response is
 *   data: {contract: 2, status, messages, completion}, with "error" beside it if the prompt failed.
 * - version 1: the LLMClient is "chatbot", with "url_chatbot", and a prompt's response is an AWS
 *   Lambda style response, whose body is a JSON string of the completion, with Smarter's own messages
 *   in body.smarter.messages. A failed prompt's body is {error: {status, message}, response}.
 *
 * Every other error is {error: {errorClass, description, status}}.
 *
 * A prompt can stream its progress, e.g. its tool calls and MCP server requests, as Server-Sent
 * Events: the request accepts text/event-stream, and the response is "progress" events, then a
 * "result" event with the same JSON as a non-streaming response. Servers that don't stream answer
 * with JSON, as before. See smarter.apps.prompt.progress.
 */
import type { ApiMessage, ChatConfig, ChatCookies, ClientContext, Contract, LLMClientConfig } from "../types";
import { getCookie, setCookie } from "./cookie";
import { SenderRoleEnum } from "./enums";
import { gettext, interpolate, ngettext } from "./i18n";

const applicationJson = "application/json";
const textEventStream = "text/event-stream";

/** The capability with which Smarter Chat asks for version 2 of the contract. */
export const CHAT_CONTRACT_V2_CAPABILITY = "chat-contract-v2";
export const CHAT_CONTRACT_V2 = 2;

export class SmarterApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "SmarterApiError";
    this.status = status;
  }
}

/** The result of a prompt: the messages to add to the thread, and the error, if it failed. */
export interface PromptResult {
  messages: ApiMessage[];
  error: string | null;
}

/** A step of a prompt that is still running, e.g. a tool call. */
export interface PromptProgressEvent {
  /** e.g. llm_request, tool_requested, tool_responded, plugin_called, mcp_tool_called */
  type: string;
  /** A short, human-readable description of the step. */
  message: string;
  [key: string]: unknown;
}

/** The http status of a response, as errorMessage() reads it. */
type ResponseStatus = Pick<Response, "status" | "statusText">;

/** The url of an api endpoint, relative to apiUrl, with the chat session's key. */
export function urlFactory(apiUrl: string, endpoint: string | null, sessionKey: string | null): string {
  const base = apiUrl.endsWith("/") ? apiUrl : `${apiUrl}/`;
  const url = new URL(endpoint || "", new URL(base, window.location.href));
  if (sessionKey) {
    url.searchParams.append("session_key", sessionKey);
  }
  return url.toString();
}

/**
 * The request headers. Any custom header must also be in Django's CORS_ALLOW_HEADERS, in
 * smarter.settings.base, for pages on other domains.
 */
export function requestHeadersFactory(cookies: ChatCookies, context: ClientContext): Record<string, string> {
  const headers: Record<string, string> = {
    Accept: applicationJson,
    "Content-Type": applicationJson,
    "X-CSRFToken": getCookie(cookies.csrfCookie, "") ?? "",
    "X-Smarter-Client": context.smarterClient,
    "X-Smarter-ClientVersion": context.smarterClientVersion,
    "X-Smarter-ClientType": "react",
    "X-Smarter-Capabilities": CHAT_CONTRACT_V2_CAPABILITY,
  };
  if (context.smarterRequestId) {
    headers["X-Smarter-RequestId"] = context.smarterRequestId;
  }
  if (context.apiKey) {
    headers.Authorization = `Token ${context.apiKey}`;
  }
  return headers;
}

function requestInitFactory(headers: Record<string, string>, body: unknown): RequestInit {
  return {
    method: "POST",
    credentials: "include",
    mode: "cors",
    headers,
    body: JSON.stringify(body),
  };
}

/** The response's JSON, or a SmarterApiError when it isn't JSON. */
async function getJson(response: Response): Promise<Record<string, unknown>> {
  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes(applicationJson)) {
    const text = await response.text();
    throw new SmarterApiError(
      interpolate(gettext("Unexpected response from the Smarter api (http %(status)s): %(text)s"), {
        status: response.status,
        text: text.slice(0, 200),
      }),
      response.status,
    );
  }
  return (await response.json()) as Record<string, unknown>;
}

/** The error message of an api error response, whatever its shape. */
export function errorMessage(json: Record<string, unknown>, response: ResponseStatus): string {
  const error = (json.error ?? (json.data as Record<string, unknown> | undefined)?.error) as unknown;
  if (typeof error === "string") {
    return error;
  }
  if (error && typeof error === "object") {
    const { message, description } = error as Record<string, unknown>;
    if (typeof message === "string") return message;
    if (typeof description === "string") return description;
  }
  return interpolate(gettext("The Smarter api returned http %(status)s %(statusText)s"), {
    status: response.status,
    statusText: response.statusText,
  }).trim();
}

/**
 * A configuration in version 2 of the contract: as is, or converted from version 1, whose keys are
 * renamed at every depth ("chatbot" for "llmclient", e.g. "url_chatbot" for "url_llmclient"). Null if
 * it has no LLMClient, or no prompt api url.
 */
export function normalizeConfig(data: unknown): ChatConfig | null {
  if (!data || typeof data !== "object") return null;
  const config = data as Record<string, unknown>;
  if (config.contract === CHAT_CONTRACT_V2) {
    const llmclient = config.llmclient as LLMClientConfig | undefined;
    return llmclient?.url_llmclient ? withLegacyChatbot(config as Contract.PromptChatApiConfig) : null;
  }
  const chatbot = config.chatbot as Record<string, unknown> | undefined;
  if (!chatbot || typeof chatbot.url_chatbot !== "string") return null;
  return withLegacyChatbot(fromLegacyKeyNames(config) as Contract.PromptChatApiConfig);
}

/**
 * A version 1 value with the key names of version 2, at every depth: the inverse of the backend's
 * renames (smarter.apps.prompt.contract.models.LEGACY_KEY_RENAMES), "chatbot" to "llmclient" and
 * "accountNumber" to "account_number". ("chat_history" is the same in both versions.)
 */
function fromLegacyKeyNames(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(fromLegacyKeyNames);
  if (!value || typeof value !== "object") return value;
  return Object.fromEntries(
    Object.entries(value).map(([key, item]) => [
      key.replaceAll("chatbot", "llmclient").replaceAll("accountNumber", "account_number"),
      fromLegacyKeyNames(item),
    ]),
  );
}

/**
 * A copy of a version 2 configuration, with the deprecated "chatbot", a read-only alias of its
 * "llmclient", for code written for version 1. The alias is not enumerable, so it is never serialized,
 * e.g. by the Console, which displays the configuration as JSON.
 */
export function withLegacyChatbot(config: Contract.PromptChatApiConfig): ChatConfig {
  const copy = { ...config };
  Object.defineProperty(copy, "chatbot", {
    get(this: Contract.PromptChatApiConfig) {
      return this.llmclient;
    },
    enumerable: false,
  });
  return copy as ChatConfig;
}

/** The config api's query parameter that asks for the configuration's diagnostic parts. */
export const VERBOSE_PARAMETER = "verbose";

/**
 * The LLMClient's configuration. A new chat session's key, and the debug mode, are saved in their
 * cookies, for the next page load.
 *
 * With verbose, the platform adds the configuration's diagnostic parts, which the Console displays:
 * the session's tool calls, the complete meta_data, and the lists of plugins and extensions. They are
 * costly to build, so the chat asks for them only while the Console displays them. A deployed
 * LLMClient's own host, and an older platform, ignore it.
 */
export async function fetchConfig(
  apiUrl: string,
  cookies: ChatCookies,
  context: ClientContext,
  verbose = false,
): Promise<ChatConfig> {
  const sessionKey = getCookie(cookies.sessionCookie, "");
  const headers = requestHeadersFactory(cookies, context);
  const init = requestInitFactory(headers, { session_key: sessionKey });
  const url = new URL(urlFactory(apiUrl, "config/", sessionKey));
  if (verbose) {
    url.searchParams.append(VERBOSE_PARAMETER, "true");
  }
  const response = await fetch(url.toString(), init);
  const json = await getJson(response);
  if (!response.ok) {
    throw new SmarterApiError(errorMessage(json, response), response.status);
  }
  const config = normalizeConfig(json.data);
  if (!config) {
    throw new SmarterApiError(gettext("The Smarter api returned an incomplete configuration."), response.status);
  }
  setCookie(cookies.sessionCookie, config.session_key);
  setCookie(cookies.debugCookie, config.debug_mode);
  return config;
}

/** The completion in a prompt response's body, which is a JSON string. */
function parseBody(json: Record<string, unknown>): Record<string, unknown> | null {
  const body = (json.data as Record<string, unknown> | undefined)?.body;
  if (typeof body === "string") {
    try {
      return JSON.parse(body) as Record<string, unknown>;
    } catch {
      return null;
    }
  }
  return body && typeof body === "object" ? (body as Record<string, unknown>) : null;
}

function smarterMessages(completion: Record<string, unknown> | null | undefined): ApiMessage[] {
  const smarter = completion?.smarter as { messages?: ApiMessage[] } | undefined;
  return Array.isArray(smarter?.messages) ? smarter.messages : [];
}

/**
 * Reads a Server-Sent Events stream, and calls onEvent with each event's name and data. Comments
 * (e.g. keepalives) and retry hints are ignored.
 */
export async function readEventStream(
  body: ReadableStream<Uint8Array>,
  onEvent: (event: string, data: string) => void,
): Promise<void> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  const dispatch = (frame: string) => {
    let event = "message";
    const data: string[] = [];
    for (const line of frame.split("\n")) {
      if (line.startsWith("event:")) event = line.slice(6).trim();
      else if (line.startsWith("data:")) data.push(line.slice(5).replace(/^ /, ""));
    }
    if (data.length > 0) onEvent(event, data.join("\n"));
  };

  for (;;) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value, { stream: !done }).replace(/\r\n?/g, "\n");
    let boundary = buffer.indexOf("\n\n");
    while (boundary >= 0) {
      dispatch(buffer.slice(0, boundary));
      buffer = buffer.slice(boundary + 2);
      boundary = buffer.indexOf("\n\n");
    }
    if (done) break;
  }
  if (buffer.trim()) dispatch(buffer);
}

/**
 * The api's JSON, and its http status, from a prompt's event stream. Progress events are passed to
 * onProgress as they arrive.
 */
async function readPromptEventStream(
  response: Response,
  onProgress: (event: PromptProgressEvent) => void,
): Promise<{ json: Record<string, unknown>; status: number }> {
  // assigned in a callback, which typescript's narrowing doesn't see.
  const received: { result: { status?: number; response?: Record<string, unknown> } | null } = { result: null };
  if (!response.body) {
    throw new SmarterApiError(gettext("The Smarter api returned an empty event stream."), response.status);
  }
  await readEventStream(response.body, (event, data) => {
    try {
      if (event === "progress") onProgress(JSON.parse(data) as PromptProgressEvent);
      else if (event === "result") received.result = JSON.parse(data) as typeof received.result;
    } catch {
      // a malformed event. The result is required, below; progress is optional.
    }
  });
  if (!received.result) {
    throw new SmarterApiError(gettext("The Smarter api's event stream ended without a result."), response.status);
  }
  const { status, response: json } = received.result;
  return { json: json ?? {}, status: status ?? response.status };
}

interface CompletionUsage {
  completion_tokens?: number;
  completion_tokens_details?: { reasoning_tokens?: number };
}

/**
 * A "smarter" message that explains a completion that the LLM stopped because it reached the
 * LLMClient's max tokens, i.e. whose finish_reason is "length", or null. A reasoning model can
 * spend all of its tokens reasoning, and then return an empty response, which is otherwise
 * displayed as nothing at all.
 */
export function maxTokensMessage(completion: Record<string, unknown> | null | undefined): ApiMessage | null {
  const choices = completion?.choices as
    { finish_reason?: string; message?: { content?: string | null } }[] | undefined;
  const choice = Array.isArray(choices) ? choices[0] : undefined;
  if (choice?.finish_reason !== "length") return null;
  const usage = completion?.usage as CompletionUsage | undefined;
  const tokens = usage?.completion_tokens;
  const reasoning = usage?.completion_tokens_details?.reasoning_tokens;
  const incomplete = !!choice.message?.content;
  let explanation: string;
  if (tokens && reasoning) {
    explanation = incomplete
      ? ngettext(
          "The LLM reached this LLMClient's max tokens of %(tokens)s completion token, %(reasoning)s of which it spent reasoning, so its response is incomplete.",
          "The LLM reached this LLMClient's max tokens of %(tokens)s completion tokens, %(reasoning)s of which it spent reasoning, so its response is incomplete.",
          tokens,
        )
      : ngettext(
          "The LLM reached this LLMClient's max tokens of %(tokens)s completion token, %(reasoning)s of which it spent reasoning, so its response is empty.",
          "The LLM reached this LLMClient's max tokens of %(tokens)s completion tokens, %(reasoning)s of which it spent reasoning, so its response is empty.",
          tokens,
        );
  } else if (tokens) {
    explanation = incomplete
      ? ngettext(
          "The LLM reached this LLMClient's max tokens of %(tokens)s completion token, so its response is incomplete.",
          "The LLM reached this LLMClient's max tokens of %(tokens)s completion tokens, so its response is incomplete.",
          tokens,
        )
      : ngettext(
          "The LLM reached this LLMClient's max tokens of %(tokens)s completion token, so its response is empty.",
          "The LLM reached this LLMClient's max tokens of %(tokens)s completion tokens, so its response is empty.",
          tokens,
        );
  } else {
    explanation = incomplete
      ? gettext("The LLM reached this LLMClient's max tokens, so its response is incomplete.")
      : gettext("The LLM reached this LLMClient's max tokens, so its response is empty.");
  }
  // Translators: defaultMaxTokens is a field of the LLMClient's manifest, which is not translated.
  const advice = gettext("Raise defaultMaxTokens in the LLMClient's manifest.");
  return {
    role: SenderRoleEnum.SMARTER,
    content: `${interpolate(explanation, { tokens, reasoning })} ${advice}`,
  };
}

/** A failed prompt's messages, with a "smarter_error" message to display, if they have none. */
function failedPrompt(messages: ApiMessage[], error: string): PromptResult {
  const hasErrorMessage = messages.some((message) => message.role === SenderRoleEnum.SMARTER_ERROR);
  return {
    messages: hasErrorMessage ? messages : [...messages, { role: SenderRoleEnum.SMARTER_ERROR, content: error }],
    error,
  };
}

/** The result of a prompt, from a version 2 response. */
function promptResultV2(json: Record<string, unknown>, response: ResponseStatus): PromptResult {
  const data = json.data as { status?: number; messages?: ApiMessage[]; completion?: Record<string, unknown> | null };
  const messages = Array.isArray(data.messages) ? data.messages : [];
  const ok = response.status >= 200 && response.status < 300 && !json.error;
  if (ok) {
    const truncated = maxTokensMessage(data.completion);
    return { messages: truncated ? [...messages, truncated] : messages, error: null };
  }
  return failedPrompt(messages, errorMessage(json, response));
}

/** The result of a prompt, from a version 1 response: a Lambda style response, whose body is a JSON string. */
function promptResultV1(json: Record<string, unknown>, response: ResponseStatus): PromptResult {
  const body = parseBody(json);
  const statusCode = (json.data as Record<string, unknown> | undefined)?.statusCode;
  const ok = response.status >= 200 && response.status < 300;

  if (ok && (statusCode === undefined || statusCode === 200) && body) {
    const truncated = maxTokensMessage(body);
    return { messages: truncated ? [...smarterMessages(body), truncated] : smarterMessages(body), error: null };
  }

  // a failed prompt: the provider's error, with the messages of the backend's response, if any.
  const bodyError = body?.error as { message?: string } | undefined;
  const error = bodyError?.message || errorMessage(json, response);
  return failedPrompt(smarterMessages(body?.response as Record<string, unknown> | undefined), error);
}

/** The result of a prompt, from the api's JSON and http status, in either version of the contract. */
function promptResult(json: Record<string, unknown>, response: ResponseStatus): PromptResult {
  const data = json.data as Record<string, unknown> | undefined;
  return data?.contract === CHAT_CONTRACT_V2 ? promptResultV2(json, response) : promptResultV1(json, response);
}

/**
 * Sends the thread to the LLMClient's prompt api. Resolves to the messages to add to the thread.
 * A failed prompt resolves too, with its error, and with a "smarter_error" message to display.
 *
 * With onProgress, the prompt's progress is requested as Server-Sent Events, and each step is
 * passed to onProgress while the prompt runs.
 */
export async function fetchPrompt(
  config: ChatConfig,
  messages: ApiMessage[],
  cookies: ChatCookies,
  context: ClientContext,
  onProgress?: (event: PromptProgressEvent) => void,
): Promise<PromptResult> {
  const sessionKey = getCookie(cookies.sessionCookie, "") || config.session_key;
  const headers = requestHeadersFactory(cookies, context);
  if (onProgress) {
    headers.Accept = `${textEventStream}, ${applicationJson}`;
  }
  const init = requestInitFactory(headers, { session_key: sessionKey, messages });
  const response = await fetch(urlFactory(config.llmclient.url_llmclient, null, sessionKey), init);

  const contentType = response.headers.get("content-type") ?? "";
  if (onProgress && contentType.includes(textEventStream)) {
    const { json, status } = await readPromptEventStream(response, onProgress);
    return promptResult(json, { status, statusText: "" });
  }
  return promptResult(await getJson(response), response);
}

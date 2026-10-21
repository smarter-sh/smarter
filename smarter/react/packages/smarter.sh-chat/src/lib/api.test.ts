import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { projectName, projectVersion } from "@/const";
import {
  API_URL,
  CONFIG_URL,
  PROMPT_URL,
  SESSION_KEY,
  apiErrorResponse,
  config,
  configV1,
  configWithHistory,
  progressEvents,
  promptErrorResponse,
  promptErrorResponseV1,
  promptMaxTokensResponse,
  promptMaxTokensResponseV1,
  promptEventStream,
  promptResponse,
  promptResponseV1,
  responseMessages,
} from "@/mocks/fixtures";
import type { ChatCookies, ClientContext } from "@/types";
import { server } from "@test/server";

import {
  CHAT_CONTRACT_V2_CAPABILITY,
  SmarterApiError,
  errorMessage,
  fetchConfig,
  VERBOSE_PARAMETER,
  fetchPrompt,
  maxTokensMessage,
  normalizeConfig,
  readEventStream,
  requestHeadersFactory,
  urlFactory,
  type PromptProgressEvent,
} from "./api";
import { cookieMetaFactory, getCookie } from "./cookie";
import { activateLanguage } from "./i18n";

const cookies: ChatCookies = {
  csrfCookie: cookieMetaFactory("csrftoken", null, "localhost"),
  sessionCookie: cookieMetaFactory("session_key", 60_000, "localhost"),
  debugCookie: cookieMetaFactory("debug", 60_000, "localhost"),
};
const context: ClientContext = { smarterClient: projectName, smarterClientVersion: projectVersion };

describe("urlFactory", () => {
  it("joins the api url and endpoint, with the session key", () => {
    expect(urlFactory("https://api.example.com/llm", "config/", "abc")).toBe(
      "https://api.example.com/llm/config/?session_key=abc",
    );
    expect(urlFactory("https://api.example.com/llm/", null, null)).toBe("https://api.example.com/llm/");
  });

  it("resolves a relative api url against the page", () => {
    expect(urlFactory("/workbench/llm-clients/x/", "config/", null)).toBe(
      "http://localhost:9357/workbench/llm-clients/x/config/",
    );
  });
});

describe("requestHeadersFactory", () => {
  beforeEach(() => {
    document.cookie = "csrftoken=the-csrf-token; path=/";
  });

  it("sends the CSRF token and identifies the client", () => {
    const headers = requestHeadersFactory(cookies, { ...context, smarterRequestId: "request-1" });
    expect(headers).toMatchObject({
      "X-CSRFToken": "the-csrf-token",
      "X-Smarter-Client": "@smarter.sh/ui-chat",
      "X-Smarter-ClientType": "react",
      "X-Smarter-RequestId": "request-1",
      "X-Smarter-Capabilities": CHAT_CONTRACT_V2_CAPABILITY,
    });
    expect(headers.Authorization).toBeUndefined();
  });

  it("sends an api key as a token", () => {
    expect(requestHeadersFactory(cookies, { ...context, apiKey: "secret" }).Authorization).toBe("Token secret");
  });
});

describe("fetchConfig", () => {
  it("returns the configuration, and saves the chat session's key", async () => {
    let body: unknown;
    server.use(
      http.post(CONFIG_URL, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json({ data: config });
      }),
    );
    const result = await fetchConfig(API_URL, cookies, context);
    expect(result.llmclient.app_name).toBe("Stackademy");
    expect(body).toEqual({ session_key: "" });
    expect(getCookie(cookies.sessionCookie)).toBe(SESSION_KEY);
  });

  it("asks for the diagnostic parts with ?verbose=true, only when verbose", async () => {
    const urls: string[] = [];
    server.use(
      http.post(CONFIG_URL, ({ request }) => {
        urls.push(request.url);
        return HttpResponse.json({ data: config });
      }),
    );
    await fetchConfig(API_URL, cookies, context);
    await fetchConfig(API_URL, cookies, context, true);
    expect(new URL(urls[0]).searchParams.has(VERBOSE_PARAMETER)).toBe(false);
    expect(new URL(urls[1]).searchParams.get(VERBOSE_PARAMETER)).toBe("true");
    expect(new URL(urls[1]).searchParams.get("session_key")).toBe(SESSION_KEY);
  });

  it("throws the api's error", async () => {
    server.use(http.post(CONFIG_URL, () => HttpResponse.json(apiErrorResponse(), { status: 404 })));
    await expect(fetchConfig(API_URL, cookies, context)).rejects.toThrow("LLMClient not found.");
  });

  it("reads version 1 of the contract, from older platforms", async () => {
    server.use(http.post(CONFIG_URL, () => HttpResponse.json({ data: configV1(configWithHistory) })));
    const result = await fetchConfig(API_URL, cookies, context);
    expect(result.llmclient.url_llmclient).toBe(PROMPT_URL);
    expect(result.llmclient.app_name).toBe("Stackademy");
    expect(result.history.prompt_tool_call_history).toEqual(configWithHistory.history.prompt_tool_call_history);
    expect(Object.keys(result)).not.toContain("chatbot");
    expect(result.chatbot.url_llmclient).toBe(PROMPT_URL);
  });

  it("throws when the api does not return JSON", async () => {
    server.use(http.post(CONFIG_URL, () => HttpResponse.text("<html>Bad gateway</html>", { status: 502 })));
    await expect(fetchConfig(API_URL, cookies, context)).rejects.toBeInstanceOf(SmarterApiError);
  });

  it("throws when the configuration is incomplete", async () => {
    server.use(http.post(CONFIG_URL, () => HttpResponse.json({ data: {} })));
    await expect(fetchConfig(API_URL, cookies, context)).rejects.toThrow("incomplete");
  });
});

describe("normalizeConfig", () => {
  it("returns a version 2 configuration as is, with the deprecated chatbot alias", () => {
    const normalized = normalizeConfig(JSON.parse(JSON.stringify(config)));
    expect(normalized).toEqual(config);
    expect(normalized?.chatbot).toBe(normalized?.llmclient);
    // the alias is never serialized.
    expect(JSON.stringify(normalized)).not.toContain('"chatbot"');
  });

  it("returns null for a configuration without an LLMClient or a prompt url", () => {
    for (const data of [null, "text", {}, { contract: 2 }, { contract: 2, llmclient: { id: 1 } }, { chatbot: {} }]) {
      expect(normalizeConfig(data)).toBeNull();
    }
  });

  it("keeps a version 1 configuration's llmclient_request_history, if it has one", () => {
    const v1 = configV1(configWithHistory) as { history: Record<string, unknown> };
    v1.history.llmclient_request_history = [{ id: 9 }];
    expect(normalizeConfig(v1)?.history.llmclient_request_history).toEqual([{ id: 9 }]);
  });
});

describe("fetchPrompt with version 1 of the contract", () => {
  it("returns the response's messages", async () => {
    server.use(http.post(PROMPT_URL, () => HttpResponse.json(promptResponseV1())));
    expect(await fetchPrompt(config, [], cookies, context)).toEqual({ messages: responseMessages, error: null });
  });

  it("returns a failed prompt's error, and its smarter_error message", async () => {
    server.use(http.post(PROMPT_URL, () => HttpResponse.json(promptErrorResponseV1(), { status: 401 })));
    const result = await fetchPrompt(config, [], cookies, context);
    expect(result.error).toBe("Incorrect API key provided.");
    expect(result.messages).toEqual([{ role: "smarter_error", content: "401 error: Incorrect API key provided." }]);
  });

  it("adds a smarter message when the LLM reached the max tokens", async () => {
    server.use(http.post(PROMPT_URL, () => HttpResponse.json(promptMaxTokensResponseV1())));
    const result = await fetchPrompt(config, [], cookies, context);
    expect(result.messages.at(-1)?.role).toBe("smarter");
  });
});

describe("fetchPrompt", () => {
  it("sends the session key and messages, and returns the response's messages", async () => {
    let body: unknown;
    let url = "";
    server.use(
      http.post(PROMPT_URL, async ({ request }) => {
        body = await request.json();
        url = request.url;
        return HttpResponse.json(promptResponse());
      }),
    );
    const messages = [{ role: "user", content: "hello" }];
    const result = await fetchPrompt(config, messages, cookies, context);
    expect(result).toEqual({ messages: responseMessages, error: null });
    expect(body).toEqual({ session_key: SESSION_KEY, messages });
    expect(url).toContain(`session_key=${SESSION_KEY}`);
  });

  it("returns a failed prompt's error, and its smarter_error message", async () => {
    server.use(http.post(PROMPT_URL, () => HttpResponse.json(promptErrorResponse(), { status: 401 })));
    const result = await fetchPrompt(config, [], cookies, context);
    expect(result.error).toBe("Incorrect API key provided.");
    expect(result.messages).toEqual([{ role: "smarter_error", content: "401 error: Incorrect API key provided." }]);
  });

  it("returns a version 2 failure's error envelope, adding a smarter_error message if it has none", async () => {
    const failure = { ...promptErrorResponse("Rate limit reached.", 429) };
    failure.data = { ...failure.data, messages: [] };
    server.use(http.post(PROMPT_URL, () => HttpResponse.json(failure, { status: 429 })));
    const result = await fetchPrompt(config, [], cookies, context);
    expect(result).toEqual({
      messages: [{ role: "smarter_error", content: "Rate limit reached." }],
      error: "Rate limit reached.",
    });
  });

  it("adds a smarter_error message when the error response has none", async () => {
    server.use(http.post(PROMPT_URL, () => HttpResponse.json({ error: "Server error" }, { status: 500 })));
    const result = await fetchPrompt(config, [], cookies, context);
    expect(result).toEqual({ messages: [{ role: "smarter_error", content: "Server error" }], error: "Server error" });
  });

  it("adds a smarter message when the LLM reached the max tokens", async () => {
    server.use(http.post(PROMPT_URL, () => HttpResponse.json(promptMaxTokensResponse())));
    const result = await fetchPrompt(config, [], cookies, context);
    expect(result.error).toBeNull();
    expect(result.messages.at(-1)).toEqual({
      role: "smarter",
      content:
        "The LLM reached this LLMClient's max tokens of 256 completion tokens, 256 of which it spent reasoning, so its response is empty. Raise defaultMaxTokens in the LLMClient's manifest.",
    });
  });

  it("treats an unparsable body as an error", async () => {
    server.use(http.post(PROMPT_URL, () => HttpResponse.json({ data: { statusCode: 200, body: "{not json" } })));
    const result = await fetchPrompt(config, [], cookies, context);
    expect(result.error).toBe("The Smarter api returned http 200 OK");
  });
});

/** A text/event-stream response, sent in the given chunks. */
function eventStreamResponse(...chunks: string[]) {
  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    start(controller) {
      chunks.forEach((chunk) => controller.enqueue(encoder.encode(chunk)));
      controller.close();
    },
  });
  return new HttpResponse(stream, { headers: { "Content-Type": "text/event-stream" } });
}

/** A ReadableStream of the given chunks. */
function streamOf(...chunks: string[]) {
  return eventStreamResponse(...chunks).body!;
}

describe("fetchPrompt, streaming its progress", () => {
  it("asks for an event stream, passes each step to onProgress, and returns the result", async () => {
    let accept: string | null = null;
    server.use(
      http.post(PROMPT_URL, ({ request }) => {
        accept = request.headers.get("Accept");
        return eventStreamResponse(promptEventStream());
      }),
    );
    const steps: PromptProgressEvent[] = [];
    const result = await fetchPrompt(config, [], cookies, context, (event) => steps.push(event));
    expect(accept).toBe("text/event-stream, application/json");
    expect(steps).toEqual(progressEvents);
    expect(result).toEqual({ messages: responseMessages, error: null });
  });

  it("reads events that are split across chunks", async () => {
    const text = promptEventStream();
    const chunks = text.match(/[\s\S]{1,7}/g)!;
    server.use(http.post(PROMPT_URL, () => eventStreamResponse(...chunks)));
    const steps: PromptProgressEvent[] = [];
    const result = await fetchPrompt(config, [], cookies, context, (event) => steps.push(event));
    expect(steps).toHaveLength(progressEvents.length);
    expect(result.error).toBeNull();
  });

  it("returns a failed prompt's error from the result event", async () => {
    server.use(http.post(PROMPT_URL, () => eventStreamResponse(promptEventStream([], promptErrorResponse(), 401))));
    const result = await fetchPrompt(config, [], cookies, context, () => {});
    expect(result.error).toBe("Incorrect API key provided.");
  });

  it("ignores malformed progress events", async () => {
    const stream = "event: progress\ndata: {not json\n\n" + promptEventStream([]);
    server.use(http.post(PROMPT_URL, () => eventStreamResponse(stream)));
    const steps: PromptProgressEvent[] = [];
    const result = await fetchPrompt(config, [], cookies, context, (event) => steps.push(event));
    expect(steps).toEqual([]);
    expect(result.error).toBeNull();
  });

  it("treats a result event without a response as an error", async () => {
    server.use(http.post(PROMPT_URL, () => eventStreamResponse("event: result\ndata: {}\n\n")));
    const result = await fetchPrompt(config, [], cookies, context, () => {});
    expect(result.error).toBeTruthy();
    expect(result.messages).toEqual([expect.objectContaining({ role: "smarter_error" })]);
  });

  it("throws when the stream has no body", async () => {
    server.use(
      http.post(PROMPT_URL, () => new HttpResponse(null, { headers: { "Content-Type": "text/event-stream" } })),
    );
    await expect(fetchPrompt(config, [], cookies, context, () => {})).rejects.toThrow("empty event stream");
  });

  it("throws when the stream ends without a result", async () => {
    server.use(http.post(PROMPT_URL, () => eventStreamResponse("event: progress\ndata: {}\n\n")));
    await expect(fetchPrompt(config, [], cookies, context, () => {})).rejects.toThrow("without a result");
  });

  it("accepts a JSON response from a server that doesn't stream", async () => {
    server.use(http.post(PROMPT_URL, () => HttpResponse.json(promptResponse())));
    const onProgress = vi.fn();
    const result = await fetchPrompt(config, [], cookies, context, onProgress);
    expect(result).toEqual({ messages: responseMessages, error: null });
    expect(onProgress).not.toHaveBeenCalled();
  });

  it("does not ask for an event stream without onProgress", async () => {
    let accept: string | null = null;
    server.use(
      http.post(PROMPT_URL, ({ request }) => {
        accept = request.headers.get("Accept");
        return HttpResponse.json(promptResponse());
      }),
    );
    await fetchPrompt(config, [], cookies, context);
    expect(accept).toBe("application/json");
  });
});

describe("readEventStream", () => {
  it("reads named events, unnamed events, and multi-line data, and ignores comments and retry hints", async () => {
    const events: [string, string][] = [];
    await readEventStream(
      streamOf("retry: 3000\n\n: keepalive\n\nevent: bulk\ndata: a\ndata: b\n\ndata: c\r\n\r\n", "data: last"),
      (event, data) => events.push([event, data]),
    );
    expect(events).toEqual([
      ["bulk", "a\nb"],
      ["message", "c"],
      ["message", "last"],
    ]);
  });
});

describe("maxTokensMessage", () => {
  it("explains a response that the max tokens cut off", () => {
    const completion = {
      choices: [{ finish_reason: "length", message: { content: "It is sunny in" } }],
      usage: { completion_tokens: 512 },
    };
    expect(maxTokensMessage(completion)?.content).toBe(
      "The LLM reached this LLMClient's max tokens of 512 completion tokens, so its response is incomplete. Raise defaultMaxTokens in the LLMClient's manifest.",
    );
  });

  it("explains an incomplete response that spent tokens reasoning, and an empty one, in the active language", () => {
    const completion = (content: string | null) => ({
      choices: [{ finish_reason: "length", message: { content } }],
      usage: { completion_tokens: 1, completion_tokens_details: { reasoning_tokens: 1 } },
    });
    expect(maxTokensMessage(completion("It"))?.content).toBe(
      "The LLM reached this LLMClient's max tokens of 1 completion token, 1 of which it spent reasoning, so its response is incomplete. Raise defaultMaxTokens in the LLMClient's manifest.",
    );
    activateLanguage("es");
    expect(maxTokensMessage({ choices: [{ finish_reason: "length", message: { content: "Hoy" } }] })?.content).toBe(
      "El LLM alcanzó el máximo de tokens de este LLMClient, así que su respuesta está incompleta. Aumenta defaultMaxTokens en el manifiesto del LLMClient.",
    );
    activateLanguage("fr");
    expect(maxTokensMessage({ ...completion(null), usage: { completion_tokens: 8 } })?.content).toBe(
      "Le LLM a atteint le nombre maximal de jetons de ce LLMClient, 8 jetons de complétion : sa réponse est donc vide. Augmentez defaultMaxTokens dans le manifeste du LLMClient.",
    );
  });

  it("explains an empty response, without its token counts", () => {
    const completion = { choices: [{ finish_reason: "length", message: { content: null } }] };
    expect(maxTokensMessage(completion)?.content).toBe(
      "The LLM reached this LLMClient's max tokens, so its response is empty. Raise defaultMaxTokens in the LLMClient's manifest.",
    );
  });

  it("is null for a completion that finished, or that has no choices", () => {
    expect(maxTokensMessage({ choices: [{ finish_reason: "stop", message: { content: "Done." } }] })).toBeNull();
    expect(maxTokensMessage({})).toBeNull();
    expect(maxTokensMessage(null)).toBeNull();
  });
});

describe("errorMessage", () => {
  const response = new Response(null, { status: 400, statusText: "Bad Request" });

  it("reads the error, whatever its shape", () => {
    expect(errorMessage({ error: { message: "message" } }, response)).toBe("message");
    expect(errorMessage({ error: { description: "description" } }, response)).toBe("description");
    expect(errorMessage({ data: { error: "nested" } }, response)).toBe("nested");
    expect(errorMessage({}, response)).toBe("The Smarter api returned http 400 Bad Request");
    expect(errorMessage({ error: { code: 1 } }, { status: 500, statusText: "" })).toBe(
      "The Smarter api returned http 500",
    );
  });
});

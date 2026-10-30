/**
 * Example data for this package's stories and tests: what the Smarter api returns, in version 2 of
 * the contract, and, for the tests of older platforms, in version 1. The configuration is a trimmed
 * copy of a real response of the config api, for the stackademy_sql LLMClient. See
 * smarter.apps.prompt.views.detailviews.prompt_config_view.PromptConfigView.
 *
 * src/contract.test.ts validates these against contract/chat-contract.schema.json.
 */
import { withLegacyChatbot } from "@/lib/api";
import type { ApiMessage, ChatConfig, Contract, SmarterChatProps } from "@/types";

export const API_URL = "http://localhost:9357/workbench/llm-clients/rMTAwMDAwMQx/";
export const CONFIG_URL = `${API_URL}config/`;
export const PROMPT_URL = "http://localhost:9357/api/v1/llm-clients/rMTAwMDAwMQx/prompt/";
export const SESSION_KEY = "e019a5c1cb2c1cb87992d2d03bccaf44c9d98406b46de5516a4fa03650038ac8";

/** The props of the chat in sandbox mode, as the web console's workbench renders it. */
export const props: SmarterChatProps = {
  apiUrl: API_URL,
  toggleMetadata: true,
  csrfCookieName: "csrftoken",
  sessionCookieName: "session_key",
  cookieDomain: "localhost",
  smarterRequestId: "storybook-request-id",
};

export const examplePrompts = [
  "Do you offer any courses on AI?",
  "My budget is $1,000. What courses can I take?",
  "I want to study programming. What do you suggest?",
];

export function makeConfig(overrides: Partial<Contract.PromptChatApiConfig> = {}): ChatConfig {
  return withLegacyChatbot({
    contract: 2,
    session_key: SESSION_KEY,
    sandbox_mode: true,
    debug_mode: false,
    llmclient: {
      id: 1,
      url_llmclient: PROMPT_URL,
      user_profile: {
        user: { username: "admin", email: "admin@smarter.sh" },
        account: { accountNumber: "3141-5926-5359" },
      },
      default_system_role: "You are a helpful assistant. DO NOT GUESS.",
      name: "stackademy_sql",
      description: "Stackademy University course catalogue inquiries using the Stackademy SQL plugin.",
      version: "1.0.0",
      deployed: false,
      provider: "openai",
      default_model: "gpt-4o-mini",
      default_temperature: 1.0,
      default_max_tokens: 1024,
      app_name: "Stackademy",
      app_assistant: "Stanley",
      app_welcome_message: "Welcome to Stackademy! How can I help you today?",
      app_example_prompts: examplePrompts,
      app_placeholder: "Ask me anything about Stackademy courses...",
      app_info_url: "https://stackademy.edu/online-courses",
      app_file_attachment: false,
      total_tools: 2,
    },
    history: {
      chat_history: [],
      prompt_tool_call_history: [],
    },
    meta_data: {
      ready: true,
      is_deployed: false,
      is_chatbot_sandbox_url: true,
      url: CONFIG_URL,
    },
    plugins: {
      meta_data: { total_plugins: 1, plugins_returned: 1 },
      plugins: [
        {
          id: 1,
          created_at: "2026-01-01T12:00:00Z",
          updated_at: "2026-01-01T12:00:00Z",
          llmclient: 1,
          plugin_meta: {
            id: 16,
            created_at: "2026-01-01T12:00:00Z",
            updated_at: "2026-01-01T12:00:00Z",
            name: "stackademy_sql",
            description: "Query the Stackademy course catalogue.",
            version: "0.1.0",
            tags: ["db", "sql"],
            annotations: {},
            plugin_class: "sql",
          },
        },
      ],
    },
    ...overrides,
  });
}

export const config = makeConfig();

/**
 * A configuration without its diagnostic parts, as the platform returns it unless the client asks
 * for them with ?verbose=true: the session's tool calls, and the list of plugins.
 */
export function leanConfig(chatConfig: ChatConfig): ChatConfig {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { prompt_tool_call_history, ...history } = chatConfig.history;
  return makeConfig({
    ...chatConfig,
    history,
    plugins: {
      meta_data: { ...chatConfig.plugins.meta_data, plugins_returned: 0 },
      plugins: [],
    },
  });
}

/**
 * A configuration in version 1 of the contract, as older platforms return it: every key that contains
 * "llmclient" is renamed to contain "chatbot", at every depth.
 */
export function configV1(chatConfig: ChatConfig = config): Record<string, unknown> {
  const rename = (value: unknown): unknown => {
    if (Array.isArray(value)) return value.map(rename);
    if (!value || typeof value !== "object") return value;
    return Object.fromEntries(
      Object.entries(value).map(([key, item]) => [key.replaceAll("llmclient", "chatbot"), rename(item)]),
    );
  };
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { contract, ...rest } = chatConfig;
  return rename(rest) as Record<string, unknown>;
}

/** A chat session in progress, whose history the config api returns. */
export const chatHistory: ApiMessage[] = [
  { role: "system", content: "You are a helpful assistant. DO NOT GUESS." },
  { role: "assistant", content: "Welcome to Stackademy! How can I help you today?" },
  { role: "user", content: "Do you offer any courses on AI?" },
  {
    role: "assistant",
    content: null,
    tool_calls: [{ id: "call_1", type: "function", function: { name: "stackademy_sql", arguments: "{}" } }],
  },
  {
    role: "tool",
    tool_call_id: "call_1",
    content: '[{"course_code": "CS210", "course_name": "Artificial Intelligence"}]',
  },
  { role: "assistant", content: "Yes! CS210 Artificial Intelligence. See [the catalogue](https://stackademy.edu)." },
];

export const configWithHistory = makeConfig({
  history: {
    ...config.history,
    chat_history: chatHistory,
    prompt_tool_call_history: [
      {
        id: 1,
        created_at: "2026-01-01T12:00:01Z",
        updated_at: "2026-01-01T12:00:01Z",
        prompt: 7,
        plugin: 16,
        function_name: "stackademy_sql",
        function_args: "{}",
        request: { inquiry_type: "courses" },
        response: [{ course_code: "CS210", course_name: "Artificial Intelligence" }],
      },
    ],
  },
});

/** The messages that the prompt api adds to the thread, in body.smarter.messages. */
export const responseMessages: ApiMessage[] = [
  { role: "smarter", content: "Smarter selected the stackademy_sql plugin." },
  { role: "assistant", content: "We offer CS210 Artificial Intelligence, for $700.00." },
];

const ENVELOPE = { api: "smarter.sh/v1", metadata: { command: "prompt", thing: "LLMClient" } };

/** A chat completion, in the format of the OpenAI api, whose last message is the response. */
function completion(messages: ApiMessage[], overrides: Record<string, unknown> = {}) {
  return {
    id: "chatcmpl-123",
    object: "chat.completion",
    choices: [{ index: 0, finish_reason: "stop", message: messages[messages.length - 1] }],
    ...overrides,
  };
}

/**
 * The prompt api's response, version 2: the messages that the prompt added to the thread, and the
 * completion, whose fields, e.g. its choices and usage, can be overridden.
 */
export function promptResponse(
  messages: ApiMessage[] = responseMessages,
  status = 200,
  overrides: Record<string, unknown> = {},
) {
  return {
    data: {
      contract: 2,
      status,
      messages,
      completion: completion(messages, overrides),
      plugins: ["stackademy_sql"],
      tools: ["smarter_plugin_0000000016"],
    },
    ...ENVELOPE,
  };
}

/**
 * The prompt api's response, version 1: an AWS Lambda style response, whose body is a JSON string,
 * with Smarter's messages in body.smarter.messages.
 */
export function promptResponseV1(
  messages: ApiMessage[] = responseMessages,
  statusCode = 200,
  overrides: Record<string, unknown> = {},
) {
  const body = { ...completion(messages, overrides), smarter: { plugins: ["stackademy_sql"], messages } };
  return {
    data: {
      isBase64Encoded: false,
      statusCode,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    },
    ...ENVELOPE,
  };
}

const MAX_TOKENS_MESSAGES: ApiMessage[] = [
  { role: "assistant", content: "" },
  {
    role: "smarter",
    content: "openai prompt charges: 3538 prompt tokens, 256 completion tokens = 3794 total tokens charged.",
  },
];
const MAX_TOKENS_COMPLETION = {
  choices: [{ index: 0, finish_reason: "length", message: { role: "assistant", content: "" } }],
  usage: { completion_tokens: 256, completion_tokens_details: { reasoning_tokens: 256 } },
};

/**
 * The response of a prompt that a reasoning model stopped at the LLMClient's max tokens: it spent
 * them all reasoning, so its response is empty.
 */
export function promptMaxTokensResponse() {
  return promptResponse(MAX_TOKENS_MESSAGES, 200, MAX_TOKENS_COMPLETION);
}

/** The same, in version 1. */
export function promptMaxTokensResponseV1() {
  return promptResponseV1(MAX_TOKENS_MESSAGES, 200, MAX_TOKENS_COMPLETION);
}

/** A failed prompt's response, version 2: its messages, with a smarter_error message, and the error envelope. */
export function promptErrorResponse(message = "Incorrect API key provided.", status = 401) {
  return {
    data: {
      contract: 2,
      status,
      messages: [{ role: "smarter_error", content: `${status} error: ${message}` }],
      completion: null,
      plugins: [],
      tools: [],
    },
    error: { errorClass: "PromptChatApiErrorLLMProvider", description: message, status },
    ...ENVELOPE,
  };
}

/** A failed prompt's response, version 1: the provider's error, and the completion, with its smarter_error message. */
export function promptErrorResponseV1(message = "Incorrect API key provided.", statusCode = 401) {
  const response = {
    id: "chatcmpl-error",
    object: "chat.completion",
    smarter: { messages: [{ role: "smarter_error", content: `${statusCode} error: ${message}` }] },
  };
  return {
    data: {
      isBase64Encoded: false,
      statusCode,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ error: { status: statusCode, message }, response }),
    },
    ...ENVELOPE,
  };
}

/** An error of the configuration or prompt apis, other than a failed prompt. */
export function apiErrorResponse(
  description = "LLMClient not found.",
  status = 404,
  errorClass = "PromptChatApiErrorNotFound",
) {
  return { error: { errorClass, description, status }, ...ENVELOPE };
}

/** A small png, as a data url, so that the stories' images need no network. */
export const IMAGE_DATA_URL =
  "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAKAAAABaCAIAAACwpMoFAAABK0lEQVR42u3b0S0DAACE4ZulL7zfMIg2JUiZohoVBMEUKghC05rubGCA6598G/yPl1N2jGLKrlFM2TOKKftGMWVoFFNGRjFlbBRTDoxiyqFRTDkyiinHRjHlxCimTIxiyqlRTDkzimlre4BiBCYwCAwCg8AgMAgMAhMYBAaBQWAQGATGP4EzNYop50YxZWYUUy6MYsrcKKZcGsWUK6OYcm0UU26MYsqtUUy5M4op90Yx5cEopjwaxZQnoxh7MIM/CAwCg8AgMAgMAhMYBAaBQWAQGAQGgTf4XfhsFFMWRjHlxSimvBrFlDejmPJuFFM+jGLKp1FM+TKKKd9GMeXHKKYsjWLKyiimrI1iyq9RjD2YwR8EBoFBYBAYBAaBCQwCg8AgMAgMAoPAG+sPxer85czgf1MAAAAASUVORK5CYII=";

/** A chat session whose assistant replied with markdown images: one inline, one linked. */
export const configWithImages = makeConfig({
  history: {
    ...config.history,
    chat_history: [
      { role: "system", content: "You are a helpful assistant. DO NOT GUESS." },
      { role: "user", content: "Show me the course banner." },
      {
        role: "assistant",
        content: `Here is the course banner:\n\n![CS210 course banner](${IMAGE_DATA_URL})\n\nand the catalogue, linked:\n\n[![the catalogue](${IMAGE_DATA_URL})](https://stackademy.edu)`,
      },
    ],
  },
});

/**
 * The styles of an LLMClient (its manifest's spec.config.styles), as the config api returns them, with
 * snake_case keys: Stackademy's colors, logo, avatars and font.
 */
export const chatStyles: Contract.PromptChatApiStyles = {
  app_logo_url: "https://cdn.smarter.sh/images/logo/smarter-crop.png",
  assistant_avatar_url: "https://cdn.smarter.sh/images/logo/smarter-crop.png",
  user_avatar_url: "https://cdn.smarter.sh/images/user-avatar.png",
  app_background_image_url: "https://cdn.smarter.sh/images/stackademy-background.png",
  app_background_image_size: "cover",
  google_font: "Nunito",
  font_size: "15px",
  border_radius: "16px",
  conversation_header: { background_color: "#14213d", color: "#ffffff", info_color: "#fca311" },
  message_list: { background_color: "rgba(255, 255, 255, 0.85)", color: "#14213d" },
  incoming_message: { background_color: "#e5e5e5", color: "#14213d", link_color: "#0b57d0" },
  outgoing_message: { background_color: "#fca311", color: "#14213d" },
  message_input: { background_color: "#ffffff", editor_background_color: "#f1f1f1", placeholder_color: "#6c757d" },
  buttons: { color: "#fca311" },
  typing_indicator: { color: "#fca311" },
};

/** A chat session with an LLMClient that has styles, whose assistant has replied. */
export const configWithStyles = makeConfig({
  llmclient: { ...config.llmclient, styles: chatStyles },
  history: {
    ...config.history,
    chat_history: [
      { role: "system", content: "You are a helpful assistant. DO NOT GUESS." },
      { role: "user", content: "Do you offer any courses on AI?" },
      {
        role: "assistant",
        content: "Yes! **CS301 Applied AI** starts next month. See the [catalogue](https://stackademy.edu).",
      },
    ],
  },
});

/** A configuration whose history has a code block, which is highlighted, with a copy button. */
export const configWithCode = makeConfig({
  history: {
    ...config.history,
    chat_history: [
      { role: "system", content: "You are a helpful assistant. DO NOT GUESS." },
      { role: "user", content: "How do I enroll in CS210 from Python?" },
      {
        role: "assistant",
        content: 'Like this:\n\n```python\nimport stackademy\n\nstackademy.enroll("CS210")\n```',
      },
    ],
  },
});

/** A configuration whose history has math, in LaTeX, which is typeset: inline, and displayed. */
export const configWithMath = makeConfig({
  history: {
    ...config.history,
    chat_history: [
      { role: "system", content: "You are a helpful assistant. DO NOT GUESS." },
      { role: "user", content: "What is the Fibonacci sequence?" },
      {
        role: "assistant",
        content: String.raw`Each term is the sum of the two before it: \(F_n = F_{n-1} + F_{n-2}\), with \(F_0 = 0\) and \(F_1 = 1\). The ratio of consecutive terms approaches the golden ratio:

\[
\varphi = \lim_{n \to \infty} \frac{F_{n+1}}{F_n} = \frac{1 + \sqrt{5}}{2} \approx 1.618
\]`,
      },
    ],
  },
});

/** A configuration whose history has a mermaid code block, which is displayed as its diagram. */
export const configWithDiagram = makeConfig({
  history: {
    ...config.history,
    chat_history: [
      { role: "system", content: "You are a helpful assistant. DO NOT GUESS." },
      { role: "user", content: "How does enrollment work?" },
      {
        role: "assistant",
        content:
          "Like this:\n\n```mermaid\ngraph TD\n  A[Browse the catalogue] --> B{Prerequisites met?}\n" +
          "  B -->|Yes| C[Enroll in CS210]\n  B -->|No| D[Take CS110 first]\n  D --> C\n```",
      },
    ],
  },
});

/** The progress of a prompt that calls a tool and an MCP server, as the prompt api streams it. */
export const progressEvents = [
  { type: "llm_request", message: "Sending the prompt to the LLM", iteration: 1 },
  { type: "tool_requested", message: "Calling tool stackademy_sql", tool: "stackademy_sql", arguments: "{}" },
  {
    type: "mcp_tool_called",
    message: "Calling MCP server github: search_code",
    mcpclient: "github",
    tool: "search_code",
  },
  { type: "tool_responded", message: "Tool stackademy_sql responded", tool: "stackademy_sql" },
  { type: "llm_request", message: "Sending the tool results to the LLM", iteration: 2 },
];

/** A prompt api response as Server-Sent Events: its progress, keepalives, and then its result. */
export function promptEventStream(
  events: object[] = progressEvents,
  response: object = promptResponse(),
  status = 200,
): string {
  const frames = events.map((event) => `event: progress\ndata: ${JSON.stringify(event)}\n\n`);
  return [
    "retry: 3000\n\n",
    ...frames,
    ": keepalive\n\n",
    `event: result\ndata: ${JSON.stringify({ status, response })}\n\n`,
  ].join("");
}

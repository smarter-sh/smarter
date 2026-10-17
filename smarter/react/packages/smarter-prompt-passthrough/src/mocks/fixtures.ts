/**
 * Example data for this package's stories and tests: what the Django api returns.
 * See smarter.apps.dashboard.views.passthrough.api.providers.
 */
import type { SessionContext } from "@smarter/common";

import type { LLMProvider } from "@/components/LLMProviders";

export const API_URL = "/api/v1/prompts/passthrough/";
export const PROVIDER_API_URL = "/dashboard/passthrough/api/providers/";

export const sessionContext: SessionContext = {
  ApiUrl: API_URL,
  csrfCookieName: "csrftoken",
  djangoSessionCookieName: "sessionid",
  cookieDomain: "localhost",
  debugMode: false,
  smarterClient: "@smarter/prompt-passthrough",
  smarterClientVersion: "0.0.0",
  smarterRequestId: "storybook-request-id",
};

export function makeProvider(id: number, name: string, overrides: Partial<LLMProvider> = {}): LLMProvider {
  return {
    id,
    tags: [],
    apiKey: { id, name: `${name}_api_key` },
    isOfficialProvider: true,
    tosAccepted: true,
    rfc1034CompliantName: name,
    tosAcceptedBy: { username: "admin", email: "admin@example.com" },
    userProfile: {
      user: { username: "admin", email: "admin@example.com" },
      account: { accountNumber: "3141-5926-5359" },
    },
    createdAt: "2026-06-01T12:00:00Z",
    updatedAt: "2026-06-15T12:00:00Z",
    name,
    description: `The ${name} API.`,
    version: "1.0.0",
    annotations: [],
    status: "verified",
    isDefault: false,
    isActive: true,
    isVerified: true,
    isFeatured: false,
    isDeprecated: false,
    isFlagged: false,
    isSuspended: false,
    baseUrl: `https://api.${name}.example.com/v1/`,
    defaultModel: `${name}-model`,
    connectivityTestPath: "models",
    logo: "",
    websiteUrl: `https://${name}.example.com`,
    ownershipRequested: null,
    contactEmail: `contact@${name}.example.com`,
    contactEmailVerified: "",
    supportEmail: `support@${name}.example.com`,
    supportEmailVerified: "",
    docsUrl: `https://docs.${name}.example.com`,
    termsOfServiceUrl: "",
    privacyPolicyUrl: "",
    tosAcceptedAt: "2026-06-01T12:00:00Z",
    ...overrides,
  };
}

/** A white mark, like the logos that providers publish for dark backgrounds. */
const WHITE_LOGO =
  "data:image/svg+xml," +
  encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><circle cx="32" cy="32" r="26" fill="none" stroke="#fff" stroke-width="7"/><circle cx="32" cy="32" r="9" fill="#fff"/></svg>',
  );

export const providers: LLMProvider[] = [
  makeProvider(1, "openai", {
    isDefault: true,
    defaultModel: "gpt-4o-mini",
    description: "OpenAI provides advanced AI models and APIs.",
    manifestUrl: "/provider/providers/rMTAwMDAwNwx/",
    apiKey: { id: 1, name: "openai_api_key", manifestUrl: "/secret/secrets/rMTAwMDAxMQx/" },
    logo: WHITE_LOGO,
    connectivityTestPath: "chat/completions",
    contactEmailVerified: "2026-06-01T12:00:00.041224Z",
    supportEmailVerified: "2026-06-01T12:00:00.041224Z",
    termsOfServiceUrl: "https://openai.example.com/terms/",
    privacyPolicyUrl: "https://openai.example.com/privacy/",
    tags: ["llm", "chat"],
    annotations: [{ "smarter.sh/purpose": "testing" }, { "smarter.sh/tier": 2 }],
  }),
  makeProvider(2, "anthropic", { defaultModel: "claude-haiku-4-5" }),
];

/** A provider that has none of the details that the Provider model allows to be empty. */
export const sparseProvider: LLMProvider = makeProvider(3, "localllm", {
  status: "unverified",
  description: "",
  isActive: false,
  isVerified: false,
  isOfficialProvider: false,
  tosAccepted: false,
  tosAcceptedBy: null,
  tosAcceptedAt: null,
  apiKey: null,
  defaultModel: null,
  connectivityTestPath: null,
  websiteUrl: null,
  docsUrl: null,
  contactEmail: null,
  supportEmail: null,
  ownershipRequested: null,
});

/** A provider that was flagged, then suspended. */
export const suspendedProvider: LLMProvider = makeProvider(4, "shadyai", {
  status: "suspended",
  isActive: false,
  isFlagged: true,
  isSuspended: true,
  ownershipRequested: "claims@shadyai.example.com",
});

export const completion = {
  id: "chatcmpl-123",
  object: "chat.completion",
  model: "gpt-4o-mini-2024-07-18",
  choices: [{ index: 0, message: { role: "assistant", content: "Hello! How can I help?" }, finish_reason: "stop" }],
  usage: { prompt_tokens: 13, completion_tokens: 7, total_tokens: 20 },
  api: "smarter.sh/v1",
  metadata: { command: "prompt", thing: "Prompt" },
};

/** The model answers with a tool call instead of text. */
export const toolCallCompletion = {
  ...completion,
  choices: [
    {
      index: 0,
      message: {
        role: "assistant",
        content: null,
        tool_calls: [
          {
            id: "call_1",
            type: "function",
            function: { name: "get_current_weather", arguments: '{"location":"San Francisco, CA"}' },
          },
        ],
      },
      finish_reason: "tool_calls",
    },
  ],
};

/** Smarter's journaled error, as the passthrough api returns it when the provider rejects a request. */
export const providerError = {
  error: {
    errorClass: "NotFoundError",
    stacktrace:
      'Traceback (most recent call last):\n  File "smarter/apps/provider/clients.py", line 197, in handler\n    response = self.create_chat_completion(data, logger_prefix)\nopenai.NotFoundError: Error code: 404\n',
    description: "Error code: 404 - The model `no-such-model` does not exist or you do not have access to it.",
    status: 400,
    cause: "Python Exception",
    thing: "Prompt",
    command: "prompt",
  },
  api: "smarter.sh/v1",
  metadata: { command: "prompt", thing: "Prompt" },
};

/**
 * Example data for this package's stories and tests: what the Django api returns.
 * See smarter.apps.llmclient.serializers.LLMClientSerializer.
 */
import type { SessionContext, UserProfile } from "@smarter/common";

import type { LLMClient } from "@/lib/Types";

export const API_URL = "/workbench/api/listview/";

/** The base url of the clone, rename and delete apis. */
export const ACTIONS_URL = API_URL;

export const sessionContext: SessionContext = {
  ApiUrl: API_URL,
  csrfCookieName: "csrftoken",
  djangoSessionCookieName: "sessionid",
  cookieDomain: "localhost",
  debugMode: false,
  smarterClient: "@smarter/prompt-list",
  smarterClientVersion: "0.0.0",
  smarterRequestId: "storybook-request-id",
};

const USER_PROFILE: UserProfile = {
  user: { username: "admin", email: "admin@example.com" },
  account: { accountNumber: "3141-5926-5359" },
};

export function makeObject(id: number, overrides: Partial<LLMClient> = {}): LLMClient {
  return {
    id,
    isAuthenticationRequired: false,
    hashedId: `hashed${id}`,
    createdAt: "2026-06-08T20:03:05Z",
    updatedAt: "2026-06-08T20:03:12Z",
    name: `example_${id}`,
    description: "An example llmclient with tool calling and Smarter Plugins.",
    version: "0.1.0",
    tags: ["gibberish", "jabberwocky"],
    annotations: [{ "smarter.sh/tests/purpose": "Provide an example configuration for OpenAI API Function Calling." }],
    userProfile: USER_PROFILE,
    functions: [
      {
        id,
        createdAt: "2026-06-08T20:03:05Z",
        updatedAt: "2026-06-08T20:03:05Z",
        name: "get_current_weather",
        llmclient: id,
      },
    ],
    plugins: [
      { id: 5, name: "example_configuration" },
      { id: 4, name: "everlasting_gobstopper" },
    ],
    customDomains: [],
    apiKeys: [],
    rfc1034CompliantName: `example-${id}`,
    defaultSystemRole: "You are a helpful llmclient.",
    baseApiDomain: "api.local.smarter.sh",
    baseDefaultHost: "3141-5926-5359.api.local.smarter.sh",
    defaultHost: `example-${id}.3141-5926-5359.api.local.smarter.sh`,
    defaultUrl: `http://example-${id}.3141-5926-5359.api.local.smarter.sh/`,
    customHost: null,
    customUrl: null,
    sandboxHost: "localhost:9357",
    sandboxUrl: `http://localhost:9357/workbench/llm-clients/hashed${id}/`,
    hostname: "localhost:9357",
    url: `http://localhost:9357/workbench/llm-clients/hashed${id}/`,
    urlLlmclient: `http://localhost:9357/api/v1/llm-clients/hashed${id}/chat/`,
    urlChatConfig: `http://localhost:9357/api/v1/llm-clients/hashed${id}/config/`,
    urlChatapp: `http://localhost:9357/workbench/llm-clients/hashed${id}/chat/`,
    manifestUrl: `http://localhost:9357/workbench/llm-clients/hashed${id}/manifest/`,
    ready: true,
    canDelete: true,
    deployed: false,
    provider: "openai",
    defaultModel: "gpt-6-luna",
    defaultTemperature: 0.5,
    defaultMaxTokens: 2048,
    appName: "Smarter Demo",
    appAssistant: "Lawrence",
    appWelcomeMessage: "Welcome to the Smarter demo!",
    appExamplePrompts: ["What is the weather in San Francisco?", "What is an Everlasting Gobstopper?"],
    appPlaceholder: "Ask me anything...",
    appInfoUrl: "https://smarter.sh",
    appBackgroundImageUrl: null,
    appLogoUrl: "https://cdn.smarter.sh/images/logo/smarter-crop.png",
    appFileAttachment: false,
    dnsVerificationStatus: "Not Verified",
    tlsCertificateIssuanceStatus: "No Certificate",
    subdomain: null,
    customDomain: null,
    ...overrides,
  };
}

/** The objects that the user owns. The last one cannot be deleted. */
export const ownedObjects: LLMClient[] = [
  makeObject(1, { name: "first_example", description: "The first example." }),
  makeObject(2, { name: "second_example", description: "The second example." }),
  makeObject(3, { name: "in_use_example", description: "An example that cannot be deleted.", canDelete: false }),
];

/** The objects that are shared with the user. */
export const sharedObjects: LLMClient[] = [
  makeObject(4, {
    name: "shared_example",
    description: "An example shared with the account.",
    userProfile: {
      user: { username: "staff", email: "staff@example.com" },
      account: { accountNumber: "3141-5926-5359" },
    },
    canDelete: false,
  }),
];

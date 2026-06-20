import type { Meta, StoryObj } from "@storybook/react";

import type { SessionContext } from "@smarter/common";
import type { LLMClient } from "@/lib/Types";

import ListView from "./Component";

const sessionContext: SessionContext = {
  ApiUrl: "/workbench/api/listview/",
  csrfCookieName: "csrftoken",
  djangoSessionCookieName: "sessionid",
  cookieDomain: "localhost",
};

const exampleLLMClientObject =     {
      "id": 10,
      "hashedId": "rMTAwMDAxMAx",
      "createdAt": "2026-06-08T20:03:05.129896Z",
      "updatedAt": "2026-06-08T20:03:12.559696Z",
      "name": "example",
      "description": "An example llm_client with tool calling and Smarter Plugins.",
      "version": "0.1.0",
      "tags": [
        "gibberish",
        "jabberwocky",
        "talk-talk-talk"
      ],
      "annotations": [
        {
          "smarter.sh/tests/focus-level": "low"
        },
        {
          "smarter.sh/tests/purpose": "Provide an example configuration for OpenAI API Function Calling."
        },
        {
          "smarter.sh/tests/last-updated": "2025-12-31"
        },
        {
          "smarter.sh/tests/documentation": "https://docs.tests.edu/example-function-calling"
        },
        {
          "smarter.sh/tests/owner": "Lawrence McDaniel"
        }
      ],
      "userProfile": {
        "user": {
          "username": "admin",
          "email": "admin@smarter.sh"
        },
        "account": {
          "accountNumber": "3141-5926-5359"
        }
      },
      "functions": [
        {
          "id": 6,
          "createdAt": "2026-06-08T20:03:05.186010Z",
          "updatedAt": "2026-06-08T20:03:05.186017Z",
          "name": "get_current_weather",
          "llmClient": 10
        }
      ],
      "plugins": [
        {
          "id": 5,
          "name": "example_configuration"
        },
        {
          "id": 4,
          "name": "everlasting_gobstopper"
        }
      ],
      "customDomains": [],
      "apiKeys": [],
      "rfc1034CompliantName": "example",
      "defaultSystemRole": "The current date/time is Tuesday, 2026-06-09T13:53:30+0000\nYou are a helpful llm_client. When given the opportunity to utilize function calling, you should always do so. This will allow you to provide the best possible responses to the user. If you are unable to provide a response, you should prompt the user for more information. If you are still unable to provide a response, you should inform the user that you are unable to help them at this time.",
      "baseApiDomain": "api.local.smarter.sh",
      "baseDefaultHost": "3141-5926-5359.api.local.smarter.sh",
      "defaultHost": "example.3141-5926-5359.api.local.smarter.sh",
      "defaultUrl": "http://example.3141-5926-5359.api.local.smarter.sh/",
      "customHost": null,
      "customUrl": null,
      "sandboxHost": "localhost:9357",
      "sandboxUrl": "http://localhost:9357/workbench/llm-clients/rMTAwMDAxMAx/",
      "manifestUrl": "http://localhost:9357/workbench/llm-clients/rMTAwMDAxMAx/manifest/",
      "hostname": "localhost:9357",
      "url": "http://localhost:9357/workbench/llm-clients/rMTAwMDAxMAx/",
      "urlLlmClient": "http://localhost:9357/api/v1/llm-clients/rMTAwMDAxMAx/chat/",
      "urlChatConfig": "http://localhost:9357/api/v1/llm-clients/rMTAwMDAxMAx/config/",
      "urlChatapp": "http://localhost:9357/workbench/llm-clients/rMTAwMDAxMAx/chat/",
      "ready": true,
      "isAuthenticationRequired": false,
      "deployed": false,
      "provider": "openai",
      "defaultModel": "gpt-4o-mini",
      "defaultTemperature": 0.5,
      "defaultMaxTokens": 2048,
      "appName": "Smarter Demo",
      "appAssistant": "Lawrence",
      "appWelcomeMessage": "Welcome to the Smarter demo!",
      "appExamplePrompts": [
        "What is the weather in San Francisco?",
        "What is an Everlasting Gobstopper?",
        "example function calling configuration"
      ],
      "appPlaceholder": "Ask me anything...",
      "appInfoUrl": "https://smarter.sh",
      "appBackgroundImageUrl": null,
      "appLogoUrl": "https://cdn.smarter.sh/images/logo/smarter-crop.png",
      "appFileAttachment": false,
      "dnsVerificationStatus": "Not Verified",
      "tlsCertificateIssuanceStatus": "No Certificate",
      "subdomain": null,
      "customDomain": null
    }


const createMockClient = (id: number, overrides: Partial<LLMClient> = {}): LLMClient => {
  const hashedId = overrides.hashedId ?? `rMTAwMDAx${id.toString().padStart(2, "0")}x`;
  const accountNumber = exampleLLMClientObject.userProfile.account.accountNumber;
  const rfc1034CompliantName = `${exampleLLMClientObject.rfc1034CompliantName}-${id}`;
  const defaultHost = `${rfc1034CompliantName}.${accountNumber}.${exampleLLMClientObject.baseApiDomain}`;
  const workbenchBase = `http://localhost:9357/workbench/llm-clients/${hashedId}`;
  const apiBase = `http://localhost:9357/api/v1/llm-clients/${hashedId}`;
  const annotations: LLMClient["annotations"] = (exampleLLMClientObject.annotations ?? []).map((annotation) =>
    Object.fromEntries(Object.entries(annotation).filter(([, value]) => value !== undefined)),
  );

  return {
    id,
    isAuthenticationRequired: exampleLLMClientObject.isAuthenticationRequired,
    hashedId,
    createdAt: exampleLLMClientObject.createdAt,
    updatedAt: new Date().toISOString(),
    name: `${exampleLLMClientObject.name}-${id}`,
    description: `${exampleLLMClientObject.description} (storybook ${id})`,
    version: exampleLLMClientObject.version,
    tags: exampleLLMClientObject.tags,
    annotations,
    userProfile: {
      user: {
        username: `storybook-${id}`,
        email: `storybook-${id}@smarter.sh`,
      },
      account: {
        accountNumber,
      },
    },
    functions: exampleLLMClientObject.functions.map((fn: any, index: number) => ({
      id: fn.id + id * 100 + index,
      createdAt: fn.createdAt,
      updatedAt: fn.updatedAt,
      name: fn.name,
      llm_client: id,
    })),
    plugins: exampleLLMClientObject.plugins,
    customDomains: exampleLLMClientObject.customDomains,
    apiKeys: exampleLLMClientObject.apiKeys,
    rfc1034CompliantName,
    defaultSystemRole: exampleLLMClientObject.defaultSystemRole,
    baseApiDomain: exampleLLMClientObject.baseApiDomain,
    baseDefaultHost: `${accountNumber}.${exampleLLMClientObject.baseApiDomain}`,
    defaultHost,
    defaultUrl: `http://${defaultHost}/`,
    customHost: null,
    customUrl: null,
    sandboxHost: exampleLLMClientObject.sandboxHost,
    sandboxUrl: `${workbenchBase}/`,
    hostname: exampleLLMClientObject.hostname,
    url: `${workbenchBase}/`,
    urlLLMClient: `${apiBase}/chat/`,
    urlChatConfig: `${apiBase}/config/`,
    urlChatapp: `${workbenchBase}/chat/`,
    urlManifest: `${workbenchBase}/manifest/`,
    ready: exampleLLMClientObject.ready,
    deployed: exampleLLMClientObject.deployed,
    provider: exampleLLMClientObject.provider,
    defaultModel: exampleLLMClientObject.defaultModel,
    defaultTemperature: exampleLLMClientObject.defaultTemperature,
    defaultMaxTokens: exampleLLMClientObject.defaultMaxTokens,
    appName: exampleLLMClientObject.appName,
    appAssistant: exampleLLMClientObject.appAssistant,
    appWelcomeMessage: exampleLLMClientObject.appWelcomeMessage,
    appExamplePrompts: exampleLLMClientObject.appExamplePrompts,
    appPlaceholder: exampleLLMClientObject.appPlaceholder,
    appInfoUrl: exampleLLMClientObject.appInfoUrl,
    appBackgroundImageUrl: exampleLLMClientObject.appBackgroundImageUrl,
    appLogoUrl: exampleLLMClientObject.appLogoUrl,
    appFileAttachment: exampleLLMClientObject.appFileAttachment,
    dnsVerificationStatus: exampleLLMClientObject.dnsVerificationStatus,
    tlsCertificateIssuanceStatus: exampleLLMClientObject.tlsCertificateIssuanceStatus,
    subdomain: null,
    customDomain: null,
    ...overrides,
  };
};

const sampleObjects: LLMClient[] = [
  createMockClient(1),
  createMockClient(2, {
    provider: "anthropic",
    defaultModel: "claude-3-5-sonnet",
    plugins: [{ id: 11, name: "web-search" }],
  }),
  createMockClient(3, {
    ready: false,
    deployed: false,
    description: "Provisioning in progress",
  }),
];

const meta: Meta<typeof ListView> = {
  title: "Prompt List/ListView",
  component: ListView,
  parameters: {
    layout: "fullscreen",
  },
  args: {
    isLoading: false,
    sessionContext,
    objects: sampleObjects,
    onRequery: () => {},
  },
};

export default meta;

type Story = StoryObj<typeof ListView>;

export const Default: Story = {};

export const Loading: Story = {
  args: {
    isLoading: true,
    objects: [],
  },
};

export const Empty: Story = {
  args: {
    isLoading: false,
    objects: [],
  },
};

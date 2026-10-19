/**
 * The pages and api responses that the stories and tests use, shaped by the contract:
 * src/contract.test.ts checks each of them against contract/llmclient-deployment.schema.json.
 */
import type { SessionContext } from "@smarter/common";

import type {
  ApiKeyActionResponse,
  DeploymentApiKey,
  DeploymentApiKeys,
  DeploymentContext,
  ErrorResponse,
  LLMClientDeploymentPage,
} from "../lib/types";

export const HASHED_ID = "rMTAwMDAzOQx";
export const DEPLOYMENT_URL = `/workbench/llm-clients/${HASHED_ID}/deployment/`;
export const CREATE_URL = `${DEPLOYMENT_URL}api-keys/create/`;
export const ATTACH_URL = `${DEPLOYMENT_URL}api-keys/attach/`;
export const DETACH_URL = `${DEPLOYMENT_URL}api-keys/detach/`;
const URL = "https://stackademy.3141-5926-5359.api.example.com";

export const session: SessionContext = {
  ApiUrl: CREATE_URL,
  csrfCookieName: "csrftoken",
  djangoSessionCookieName: "sessionid",
  cookieDomain: "localhost",
  debugMode: false,
  smarterClient: "@smarter/llmclient-deployment",
  smarterClientVersion: "0.1.0",
  smarterRequestId: "test-request-id",
};

export const MANIFEST_YAML = `apiVersion: smarter.sh/v1
kind: LLMClient
metadata:
  name: stackademy
  description: Answers questions about <courses>.
spec:
  config:
    prompt:
      defaultSystemRole: |
        You are a helpful assistant.

        Answer in <b>one</b> sentence.
      deployed: true
      appExamplePrompts:
        - What courses are there?
      defaultMaxTokens: 2048
status:
  accountNumber: 3141-5926-5359`;

export function makeApiKey(overrides: Partial<DeploymentApiKey> = {}): DeploymentApiKey {
  return {
    keyId: "6f1d2c3b-4a5e-4f60-8172-839405a6b7c8",
    name: "my_site_chat",
    description: "The chat on www.example.com",
    isActive: true,
    owner: "admin",
    lastUsedAt: "2026-10-18T12:00:00Z",
    isAttached: false,
    ...overrides,
  };
}

export const firstApiKey = makeApiKey();
export const secondApiKey = makeApiKey({
  keyId: "0a1b2c3d-4e5f-4061-8273-94a5b6c7d8e9",
  name: "intranet",
  description: "",
  isActive: false,
  lastUsedAt: null,
});

export function makeApiKeys(overrides: Partial<DeploymentApiKeys> = {}): DeploymentApiKeys {
  return {
    apiKeys: [firstApiKey, secondApiKey],
    attached: null,
    canManage: true,
    canCreate: true,
    createUrl: CREATE_URL,
    attachUrl: ATTACH_URL,
    detachUrl: DETACH_URL,
    ...overrides,
  };
}

/** The workbench's page of a deployed, public LLMClient that the user owns. */
export function makePage(overrides: Partial<LLMClientDeploymentPage> = {}): LLMClientDeploymentPage {
  return {
    mode: "workbench",
    llmclient: {
      name: "stackademy",
      appName: "Stackademy Support Bot",
      examplePrompts: ["What courses are there?", "Is your program free?"],
      provider: "openai",
      model: "gpt-6-luna",
      version: "1.0.0",
      url: URL,
      workbenchUrl: `/workbench/llm-clients/${HASHED_ID}/prompt/`,
    },
    deployed: true,
    authenticated: false,
    manifestYaml: MANIFEST_YAML,
    snippets: {
      deployCommand: "smarter deploy llmclient stackademy",
      deployCommands: "smarter apply -f stackademy.yaml\nsmarter deploy llmclient stackademy",
      configCommand: `curl -X POST ${URL}/config/ \\\n  -H "Content-Type: application/json"`,
      promptCommand: `curl -X POST ${URL}/prompt/ \\\n  -H "Content-Type: application/json" \\\n  -d '{"messages":[{"role":"user","content":"What courses are there?"}]}'`,
      sessionConfigCommand: `curl -X POST ${URL}/config/ \\\n  -H "Content-Type: application/json" \\\n  -d '{"session_key":"<SESSION-KEY>"}'`,
      sessionPromptCommand: `curl -X POST ${URL}/prompt/ \\\n  -H "Content-Type: application/json" \\\n  -d '{"session_key":"<SESSION-KEY>","messages":[{"role":"user","content":"What courses are there?"}]}'`,
      exampleResponse: '{\n  "api": "smarter.sh/v1",\n  "data": {\n    "status": 200\n  }\n}',
      allowedOriginsYaml: "spec:\n  config:\n    prompt:\n      allowedOrigins:\n        - https://www.example.com",
      apiKeyYaml: "spec:\n  apiKey: <API-KEY-NAME>",
      drupalInstallCommands: "composer require smarter-sh/smarter-drupal\ndrush pm:install smarter_chat",
      npmInstallCommand: "npm install @smarter.sh/ui-chat",
      embedHtml: `<script src="https://cdn.jsdelivr.net/npm/@smarter.sh/ui-chat@0/dist/embed.js"\n  data-chatbot="${URL}/" async></script>`,
      embedHtmlWithApiKey: `<script src="https://cdn.jsdelivr.net/npm/@smarter.sh/ui-chat@0/dist/embed.js"\n  data-chatbot="${URL}/"\n  data-api-key="<YOUR-API-KEY>" async></script>`,
      reactSnippet: 'import { SmarterChat } from "@smarter.sh/ui-chat";',
      reactSnippetWithApiKey:
        'import { SmarterChat } from "@smarter.sh/ui-chat";\n// apiKey={import.meta.env.VITE_SMARTER_API_KEY}',
      createApiKeyCommand: "python manage.py create_api_key \\\n  --account_number 3141-5926-5359",
      switchCommand: "python manage.py waffle_switch enable_llmclient_endpoints_page off",
    },
    links: {
      apiKeysUrl: "https://platform.example.com/api-keys/",
      marketingSiteUrl: "https://smarter.sh",
      docsUrl: "https://docs.smarter.sh",
      logoUrl: "https://cdn.example.com/images/logo/smarter-crop.png",
      productName: "The Smarter Project",
      productDescription: "An open source, no-code AI authoring platform designed for instructional use.",
    },
    ownership: {
      owner: "Ada Lovelace (admin)",
      canEdit: true,
      llmclientListUrl: "/workbench/",
      ownershipDocsUrl:
        "https://docs.smarter.sh/en/latest/smarter-resources/account/models/metadata_with_ownership.html",
    },
    apiKeys: makeApiKeys(),
    ...overrides,
  };
}

/** The workbench's page. */
export const workbenchPage = makePage();

/** The page at the deployed LLMClient's url, which anyone can open: no owner, no api keys. */
export const publicPage = makePage({ mode: "public", ownership: null, apiKeys: null });

/** An LLMClient that isn't deployed yet, without its manifest or example prompts. */
export const notDeployedPage = makePage({
  deployed: false,
  manifestYaml: null,
  llmclient: { ...workbenchPage.llmclient, examplePrompts: [], provider: null, model: null, version: null },
});

/** An LLMClient whose url requires its attached api key. */
export const authenticatedPage = makePage({
  authenticated: true,
  apiKeys: makeApiKeys({
    attached: { name: firstApiKey.name, isActive: true },
    apiKeys: [{ ...firstApiKey, isAttached: true }, secondApiKey],
  }),
});

/** An LLMClient whose attached api key is turned off. */
export const inactiveKeyPage = makePage({
  apiKeys: makeApiKeys({
    attached: { name: secondApiKey.name, isActive: false },
    apiKeys: [firstApiKey, { ...secondApiKey, isAttached: true }],
  }),
});

/** An LLMClient that another user shares with a user who isn't an account admin. */
export const sharedPage = makePage({
  ownership: { ...workbenchPage.ownership!, canEdit: false },
  apiKeys: makeApiKeys({ apiKeys: [], canManage: false, canCreate: false }),
});

export const workbenchContext: DeploymentContext = { page: workbenchPage, session };
export const publicContext: DeploymentContext = { page: publicPage, session: null };

export const SECRET = "3e8c1f0a.d41d8cd98f00b204e9800998ecf8427e";

/** The response to creating my_new_key, attached. */
export const createdResponse: ApiKeyActionResponse = {
  page: makePage({
    authenticated: true,
    apiKeys: makeApiKeys({
      attached: { name: "my_new_key", isActive: true },
      apiKeys: [
        makeApiKey({ keyId: "11111111-2222-4333-8444-555555555555", name: "my_new_key", isAttached: true }),
        firstApiKey,
        secondApiKey,
      ],
    }),
  }),
  newApiKey: { name: "my_new_key", secret: SECRET },
};

/** The response to attaching my_site_chat. */
export const attachedResponse: ApiKeyActionResponse = { page: authenticatedPage, newApiKey: null };

/** The response to detaching the api key. */
export const detachedResponse: ApiKeyActionResponse = { page: workbenchPage, newApiKey: null };

export const duplicateNameError: ErrorResponse = {
  error: "You already have an api key named my_site_chat.",
  code: "duplicate_name",
};

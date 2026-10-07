/**
 * Example data for this package's stories and tests: what the Django api returns.
 * See smarter.apps.llmhost.serializers.LLMHostSerializer.
 */
import type { SessionContext, UserProfile } from "@smarter/common";

import type { LLMHost } from "@/lib/Types";

export const API_URL = "/llmhost/react-integration/api/listview/";

/** The base url of the clone, rename and delete apis. */
export const ACTIONS_URL = API_URL.replace(/listview\/$/, "");

export const sessionContext: SessionContext = {
  ApiUrl: API_URL,
  csrfCookieName: "csrftoken",
  djangoSessionCookieName: "sessionid",
  cookieDomain: "localhost",
  debugMode: false,
  smarterClient: "@smarter/llmhost-list",
  smarterClientVersion: "0.0.0",
  smarterRequestId: "storybook-request-id",
};

const USER_PROFILE: UserProfile = {
  user: { username: "admin", email: "admin@example.com" },
  account: { accountNumber: "3141-5926-5359" },
};

export function makeObject(id: number, overrides: Partial<LLMHost> = {}): LLMHost {
  return {
    id,
    hashedId: `hashed${id}`,
    createdAt: "2026-06-01T12:00:00Z",
    updatedAt: "2026-06-15T12:00:00Z",
    name: `example_${id}`,
    description: `An example, number ${id}.`,
    version: "1.0.0",
    tags: ["example"],
    annotations: [],
    userProfile: USER_PROFILE,
    manifestUrl: `/llmhost/llmhosts/hashed${id}/`,
    canDelete: true,
    ready: true,
    rfc1034CompliantName: `example-${id}`,
    baseUrl: "",
    spec: {},
    modelSource: "huggingface",
    modelRepository: "meta-llama/Llama-3.2-3B-Instruct",
    modelRevision: "main",
    modelTask: "text-generation",
    servedModelName: "llama-3.2-3b-instruct",
    license: "llama3.2",
    modelArchitecture: "LlamaForCausalLM",
    parameterCount: 3200000000,
    contextWindow: 131072,
    quantization: "bf16",
    embeddingDimensions: null,
    supportsStreaming: true,
    supportsFunctionCalling: true,
    supportsVision: false,
    supportsReasoning: false,
    inferenceEngine: "vllm",
    apiFormat: "openai_compatible",
    apiKeySecret: null,
    compute: 1,
    gpuType: "L4",
    gpuCount: 1,
    vramRequiredGb: 16,
    replicas: 1,
    costPerHour: "0.9776",
    status: "active",
    statusMessage: "",
    isActive: true,
    readyReplicas: 1,
    endpointUrl: "http://example.llmhost.svc.cluster.local:8000",
    publicUrl: "",
    healthCheckUrl: "http://example.llmhost.svc.cluster.local:8000/health",
    lastHealthCheckAt: "2026-06-20T12:00:00Z",
    lastHealthOk: true,
    deployedAt: "2026-06-10T12:00:00Z",
    ...overrides,
  };
}

/** The objects that the user owns. The last one cannot be deleted. */
export const ownedObjects: LLMHost[] = [
  makeObject(1, { name: "first_example", description: "The first example." }),
  makeObject(2, { name: "second_example", description: "The second example." }),
  makeObject(3, { name: "in_use_example", description: "An example that cannot be deleted.", canDelete: false }),
];

/** The objects that are shared with the user. */
export const sharedObjects: LLMHost[] = [
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

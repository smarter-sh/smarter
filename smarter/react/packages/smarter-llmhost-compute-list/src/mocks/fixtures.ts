/**
 * Example data for this package's stories and tests: what the Django api returns.
 * See smarter.apps.llmhost.serializers.LLMHostComputeSerializer.
 */
import type { SessionContext, UserProfile } from "@smarter/common";

import type { LLMHostCompute } from "@/lib/Types";

export const API_URL = "/llmhost/compute/react-integration/api/listview/";

/** The base url of the clone, rename and delete apis. */
export const ACTIONS_URL = API_URL.replace(/listview\/$/, "");

export const sessionContext: SessionContext = {
  ApiUrl: API_URL,
  csrfCookieName: "csrftoken",
  djangoSessionCookieName: "sessionid",
  cookieDomain: "localhost",
  debugMode: false,
  smarterClient: "@smarter/llmhost-compute-list",
  smarterClientVersion: "0.0.0",
  smarterRequestId: "storybook-request-id",
};

const USER_PROFILE: UserProfile = {
  user: { username: "admin", email: "admin@example.com" },
  account: { accountNumber: "3141-5926-5359" },
};

export function makeObject(id: number, overrides: Partial<LLMHostCompute> = {}): LLMHostCompute {
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
    manifestUrl: `/llmhost/compute/hashed${id}/`,
    canDelete: true,
    ready: true,
    rfc1034CompliantName: `example-${id}`,
    baseUrl: "",
    spec: {},
    instanceType: "g6.2xlarge",
    cpu: 8,
    memoryGb: 32,
    gpuType: "L4",
    gpuCount: 1,
    gpuMemoryGb: 24,
    maxNodes: 2,
    pricePerHour: "0.9776",
    nodegroupName: `smarter-alpha-${id}-gpu-l4-1x`,
    nodegroupStatus: "ACTIVE",
    desiredNodes: 1,
    readyNodes: 1,
    statusMessage: "",
    lastReconciledAt: "2026-06-20T12:00:00Z",
    llmhostCount: 1,
    ...overrides,
  };
}

/** The objects that the user owns. The last one cannot be deleted. */
export const ownedObjects: LLMHostCompute[] = [
  makeObject(1, { name: "first_example", description: "The first example." }),
  makeObject(2, { name: "second_example", description: "The second example." }),
  makeObject(3, { name: "in_use_example", description: "An example that cannot be deleted.", canDelete: false }),
];

/** The objects that are shared with the user. */
export const sharedObjects: LLMHostCompute[] = [
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

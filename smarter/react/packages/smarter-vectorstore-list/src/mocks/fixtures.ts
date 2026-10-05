/**
 * Example data for this package's stories and tests: what the Django api returns.
 * See smarter.apps.vectorstore.serializers.VectorstoreSerializer.
 */
import type { SessionContext, UserProfile } from "@smarter/common";

import type { Vectorstore } from "@/lib/Types";

export const API_URL = "/vectorstore/react-integration/api/listview/";

/** The base url of the clone, rename and delete apis. */
export const ACTIONS_URL = API_URL.replace(/listview\/$/, "");

export const sessionContext: SessionContext = {
  ApiUrl: API_URL,
  csrfCookieName: "csrftoken",
  djangoSessionCookieName: "sessionid",
  cookieDomain: "localhost",
  debugMode: false,
  smarterClient: "@smarter/vectorstore-list",
  smarterClientVersion: "0.0.0",
  smarterRequestId: "storybook-request-id",
};

const USER_PROFILE: UserProfile = {
  user: { username: "admin", email: "admin@example.com" },
  account: { accountNumber: "3141-5926-5359" },
};

export function makeObject(id: number, overrides: Partial<Vectorstore> = {}): Vectorstore {
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
    manifestUrl: `/vectorstore/vectorstores/hashed${id}/`,
    canDelete: true,
    spec: {},
    backend: "qdrant",
    hosting: "self_hosted",
    connection: null,
    isActive: true,
    dimension: 1536,
    metric: "cosine",
    deletionProtection: false,
    embeddingsProvider: "openai",
    embeddingsModel: "text-embedding-3-small",
    status: "ready",
    statusMessage: "",
    indexName: `example-${id}`,
    endpointUrl: "http://example.qdrant.svc.cluster.local:6333",
    apiKeySecret: null,
    vectorCount: 1200,
    documentCount: 40,
    snapshotCount: 1,
    stats: {},
    deployedAt: "2026-06-10T12:00:00Z",
    lastCheckedAt: "2026-06-20T12:00:00Z",
    lastSnapshotAt: null,
    lastMaintenanceAt: null,
    ...overrides,
  };
}

/** The objects that the user owns. The last one cannot be deleted. */
export const ownedObjects: Vectorstore[] = [
  makeObject(1, { name: "first_example", description: "The first example." }),
  makeObject(2, { name: "second_example", description: "The second example." }),
  makeObject(3, { name: "in_use_example", description: "An example that cannot be deleted.", canDelete: false }),
];

/** The objects that are shared with the user. */
export const sharedObjects: Vectorstore[] = [
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

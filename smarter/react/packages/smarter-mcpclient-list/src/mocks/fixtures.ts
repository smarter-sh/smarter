/**
 * Example data for this package's stories and tests: what the Django api returns.
 * See smarter.apps.mcpclient.serializers.MCPClientSerializer.
 */
import type { SessionContext, UserProfile } from "@smarter/common";

import type { MCPClient } from "@/lib/Types";

export const API_URL = "/mcpclient/react-integration/api/listview/";

/** The base url of the clone, rename and delete apis. */
export const ACTIONS_URL = API_URL.replace(/listview\/$/, "");

export const sessionContext: SessionContext = {
  ApiUrl: API_URL,
  csrfCookieName: "csrftoken",
  djangoSessionCookieName: "sessionid",
  cookieDomain: "localhost",
  debugMode: false,
  smarterClient: "@smarter/mcpclient-list",
  smarterClientVersion: "0.0.0",
  smarterRequestId: "storybook-request-id",
};

const USER_PROFILE: UserProfile = {
  user: { username: "admin", email: "admin@example.com" },
  account: { accountNumber: "3141-5926-5359" },
};

export function makeObject(id: number, overrides: Partial<MCPClient> = {}): MCPClient {
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
    manifestUrl: `/mcpclient/mcpclients/hashed${id}/`,
    canDelete: true,
    ready: true,
    rfc1034CompliantName: `example-${id}`,
    status: "connected",
    transport: "http",
    endpointUrl: "https://mcp.example.com/mcp",
    command: "",
    headers: null,
    timeout: 30,
    authType: "api_key",
    credentials: "example_mcp_api_key",
    apiKeyHeader: "Authorization",
    allowedTools: [],
    allowedResources: [],
    includeInstructions: true,
    cacheTtl: 300,
    isActive: true,
    priority: 100,
    protocolVersion: "2025-06-18",
    serverName: "example-mcp-server",
    serverVersion: "1.0.0",
    tools: ["search", "fetch"],
    lastConnectedAt: "2026-06-20T12:00:00Z",
    lastError: null,
    ...overrides,
  };
}

/** The objects that the user owns. The last one cannot be deleted. */
export const ownedObjects: MCPClient[] = [
  makeObject(1, { name: "first_example", description: "The first example." }),
  makeObject(2, { name: "second_example", description: "The second example." }),
  makeObject(3, { name: "in_use_example", description: "An example that cannot be deleted.", canDelete: false }),
];

/** The objects that are shared with the user. */
export const sharedObjects: MCPClient[] = [
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

/**
 * Example data for this package's stories and tests: what the Django api returns.
 * See smarter.lib.drf.serializers.SmarterAuthTokenSerializer.
 */
import type { SessionContext, UserProfile } from "@smarter/common";

import type { AuthToken } from "@/lib/Types";

export const API_URL = "/authtoken/react-integration/api/listview/";

/** The base url of the clone, rename and delete apis. */
export const ACTIONS_URL = API_URL.replace(/listview\/$/, "");

export const sessionContext: SessionContext = {
  ApiUrl: API_URL,
  csrfCookieName: "csrftoken",
  djangoSessionCookieName: "sessionid",
  cookieDomain: "localhost",
  debugMode: false,
  smarterClient: "@smarter/authtoken-list",
  smarterClientVersion: "0.0.0",
  smarterRequestId: "storybook-request-id",
};

const USER_PROFILE: UserProfile = {
  user: { username: "admin", email: "admin@example.com" },
  account: { accountNumber: "3141-5926-5359" },
};

export function makeObject(id: number, overrides: Partial<AuthToken> = {}): AuthToken {
  return {
    id: `00000000-0000-0000-0000-00000000000${id}`,
    hashedId: `hashed${id}`,
    createdAt: "2026-06-01T12:00:00Z",
    updatedAt: "2026-06-15T12:00:00Z",
    name: `example_${id}`,
    description: `An example, number ${id}.`,
    version: "1.0.0",
    tags: ["example"],
    annotations: [],
    userProfile: USER_PROFILE,
    manifestUrl: `/authtoken/authtokens/hashed${id}/`,
    canDelete: true,
    ready: true,
    lastAccessed: "2026-06-20T12:00:00Z",
    expiresAt: null,
    ...overrides,
  };
}

/** The objects that the user owns. The last one cannot be deleted. */
export const ownedObjects: AuthToken[] = [
  makeObject(1, { name: "first_example", description: "The first example." }),
  makeObject(2, { name: "second_example", description: "The second example." }),
  makeObject(3, { name: "in_use_example", description: "An example that cannot be deleted.", canDelete: false }),
];

/** The objects that are shared with the user. */
export const sharedObjects: AuthToken[] = [
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

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

export const providers: LLMProvider[] = [
  makeProvider(1, "openai", { isDefault: true, defaultModel: "gpt-4o-mini" }),
  makeProvider(2, "anthropic", { defaultModel: "claude-haiku-4-5" }),
];

export const completion = {
  id: "chatcmpl-123",
  object: "chat.completion",
  choices: [{ index: 0, message: { role: "assistant", content: "Hello! How can I help?" }, finish_reason: "stop" }],
};

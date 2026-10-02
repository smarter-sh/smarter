/**
 * Central type definitions for the Proxy List React application.
 *
 * A Proxy is passthrough access to a 3rd party LLM provider's API, e.g. OpenAI's or
 * Anthropic's, with an API key that Smarter keeps in a Secret. Callers use the provider's own
 * SDK, with the Proxy's URL as its base URL, and a Smarter API key in place of the provider's.
 *
 * Exports:
 *   - Proxy: the Proxy objects, as smarter.apps.proxy.serializers.ProxySerializer serializes them.
 *   - Component props interfaces.
 *
 * Usage:
 *   Import these types to ensure type safety and consistency across components and API calls.
 */
import type { SessionContext, Annotations, Tags, UserProfile } from "@smarter/common";

// ----------------------------------------------------------------------------
// Proxy Definition
// ----------------------------------------------------------------------------
export type Proxy = {
  id: number;
  hashedId: string;
  createdAt: string;
  updatedAt: string;
  name: string;
  description: string;
  version: string;
  tags: Tags;
  annotations: Annotations;
  userProfile: UserProfile;
  /** The URL of the Proxy's detail view in the web console, which renders its manifest. */
  manifestUrl: string;

  // --- Where it forwards to ---
  /** The id of the Provider whose API the Proxy forwards to. */
  provider: number;
  providerName: string;
  /** The Proxy's own base URL. Empty if the Provider's is used. */
  baseUrl: string;
  /** The base URL to which requests are forwarded: baseUrl, else the Provider's. */
  upstreamUrl: string;

  // --- The provider's API key ---
  /** The id of the Proxy's own API key Secret, or null if the Provider's is used. */
  apiKeySecret: number | null;
  /** The name of the Secret whose API key is added to requests: the Proxy's, else the Provider's. Null if none. */
  apiKeySecretName: string | null;
  /** The header in which the provider expects its API key, e.g. "Authorization" or "x-api-key". */
  authHeader: string;
  /** The prefix of the API key in the header, e.g. "Bearer", or empty. */
  authScheme: string;

  /** Headers added to every request, e.g. {"anthropic-version": "2023-06-01"}. */
  headers: Record<string, string>;
  /** Glob patterns of the paths that callers may use. Empty allows every path. */
  allowedPaths: string[];
  /** Seconds. */
  timeout: number;
  isActive: boolean;

  /** The path of the Proxy's passthrough endpoint, e.g. "/api/v1/proxy/openai/". Empty if disabled. */
  url: string;
};

// ----------------------------------------------------------------------------
// Component Props Interfaces
// ----------------------------------------------------------------------------
export interface ProxyCardViewProps {
  sessionContext: SessionContext;
  objects: Proxy[];
  onRequery: () => void;
}

export interface ProxyListViewProps {
  isLoading: boolean;
  ghostRows: number;
  sessionContext: SessionContext;
  objects: Proxy[];
  onRequery: () => void;
}

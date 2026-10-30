/**
 * @file Types.tsx
 * @module llmclient_list/lib/Types
 *
 * Central type definitions for the LLMClient List React application.
 *
 * This module exports TypeScript types and interfaces used throughout the DetailView,
 * llmclient, and API response layers. It provides strong typing for user, plugin,
 * llmclient, API response, and session context data structures.
 *
 * Exports:
 *   - TabKey: Type for tab keys ("user" | "shared").
 *   - Plugin: Type for plugin objects.
 *   - MCPClient, Guardrail: Types for an llmclient's MCPClients and guardrails.
 *   - Tool: Type for one of an llmclient's functions, plugins, MCPClients or guardrails.
 *   - LLMClientCustomDomain, LLMClientAPIKey: Types for an llmclient's custom domain and api keys.
 *   - User, UserProfile: Types for user and profile data.
 *   - LLMClient: Type for llmclient configuration and metadata.
 *   - SessionContext: Type for session and authentication context.
 *
 * Usage:
 *   Import these types to ensure type safety and consistency across components and API calls.
 */
import type { SessionContext, Sorting, Annotations, Filtering, Tags, UserProfile } from "@smarter/common";
export type TabKey = "user" | "shared";

export type Plugin = {
  id: number;
  name: string;
};

export type MCPClient = {
  id: number;
  name: string;
};

export type Guardrail = {
  id: number;
  name: string;
};

/** One of an llmclient's functions, plugins or MCPClients. Guardrails are not tools. */
export type Tool = {
  id: number;
  name: string;
  kind: "Function" | "Plugin" | "MCPClient";
};

/** The custom domain of an llmclient. See smarter.apps.llmclient.serializers.LLMClientCustomDomainSerializer. */
export type LLMClientCustomDomain = {
  domainName?: string;
  verificationStatus?: string;
  [field: string]: unknown;
};

/**
 * An api key of an llmclient: its SmarterAuthToken's public key_id, never the key itself.
 * See smarter.apps.llmclient.serializers.LLMClientAPIKeySerializer.
 */
export type LLMClientAPIKey = {
  apiKey?: string;
  [field: string]: unknown;
};

export type Function = {
  llmclient: number;
  createdAt: string;
  id: number;
  name: string;
  updatedAt: string;
};

export type LLMClient = {
  id: number;
  isAuthenticationRequired: boolean; // ADD ME PLEASE
  hashedId: string;
  createdAt: string;
  updatedAt: string;
  name: string;
  description: string;
  version: string;
  tags: Tags;
  annotations: Annotations;
  userProfile: UserProfile;
  functions: Function[];
  plugins: Array<Plugin>;
  mcpclients: MCPClient[];
  guardrails: Guardrail[];
  tools: Tool[]; // functions, plugins, mcpclients and guardrails, in that order
  customDomains: LLMClientCustomDomain[];
  apiKeys: LLMClientAPIKey[];
  rfc1034CompliantName: string;
  defaultSystemRole: string;
  baseApiDomain: string;
  baseDefaultHost: string;
  defaultHost: string;
  defaultUrl: string;
  customHost: string | null;
  customUrl: string | null;
  sandboxHost: string;
  sandboxUrl: string;
  hostname: string;
  url: string;
  urlLlmclient: string;
  urlChatConfig: string;
  urlChatapp: string;
  manifestUrl: string; // the web console page that renders the llmclient's manifest
  /** The url of the llmclient's detail: its manifest, what it uses, and what uses it. See ResourceDetail. */
  detailUrl: string | null;
  ready: boolean;
  canDelete: boolean; // false if other resources depend on it, or you may not delete it
  deployed: boolean;
  provider: string;
  defaultModel: string;
  defaultTemperature: number;
  defaultMaxTokens: number;
  appName: string;
  appAssistant: string;
  appWelcomeMessage: string;
  appExamplePrompts: string[];
  appPlaceholder: string;
  appInfoUrl: string;
  appFileAttachment: boolean;
  allowedOrigins: string[];
  styles: LLMClientStyles | null; // the manifest's spec.config.styles, with its camelCase keys
  dnsVerificationStatus: string;
  tlsCertificateIssuanceStatus: string;
  subdomain: string | null;
  customDomain: string | null;
};

/** The look of an LLMClient's chat: its manifest's spec.config.styles. Only the settings it has are present. */
export interface LLMClientStyles {
  appLogoUrl?: string | null;
  appBackgroundImageUrl?: string | null;
  googleFont?: string | null;
  fontFamily?: string | null;
  [setting: string]: unknown;
}

// ----------------------------------------------------------------------------
// Component Props Interfaces
// ----------------------------------------------------------------------------
export interface LLMClientDetailViewProps {
  sessionContext: SessionContext;
  object: LLMClient;
  onRequery: () => void;
  filtering?: Filtering;
}

export interface LLMClientListViewProps {
  isLoading: boolean;
  ghostRows: number;
  sessionContext: SessionContext;
  objects: LLMClient[];
  onRequery: () => void;
  sorting?: Sorting;
}

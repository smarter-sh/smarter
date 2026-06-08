/**
 * @file Types.tsx
 * @module prompt_list/lib/Types
 *
 * Central type definitions for the Prompt List React application.
 *
 * This module exports TypeScript types and interfaces used throughout the CardView,
 * llm_client, and API response layers. It provides strong typing for user, plugin,
 * llm_client, API response, and session context data structures.
 *
 * Exports:
 *   - TabKey: Type for tab keys ("user" | "shared").
 *   - Plugin: Type for plugin objects.
 *   - User, UserProfile: Types for user and profile data.
 *   - LLMClient: Type for llm_client configuration and metadata.
 *   - SessionContext: Type for session and authentication context.
 *
 * Usage:
 *   Import these types to ensure type safety and consistency across components and API calls.
 */
import type { Annotations, Tags } from "@smarter/common";
export type TabKey = "user" | "shared";

export type Plugin = {
  id: number;
  name: string;
};

export type User = {
  username: string;
  email: string;
};
export type UserProfile = {
  user: User;
  account?: {
    accountNumber: string;
  };
};

export type Function = {
  llm_client: number;
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
  customDomains: any[];
  apiKeys: any[];
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
  urlLLMClient: string;
  urlChatConfig: string;
  urlChatapp: string;
  urlManifest: string; // ADD ME PLEASE
  ready: boolean;
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
  appBackgroundImageUrl: string | null;
  appLogoUrl: string | null;
  appFileAttachment: boolean;
  dnsVerificationStatus: string;
  tlsCertificateIssuanceStatus: string;
  subdomain: string | null;
  customDomain: string | null;
};

export type SessionContext = {
  ApiUrl: string;
  csrfCookieName: string;
  djangoSessionCookieName: string;
  cookieDomain: string;
};

/**
 * Central type definitions for the Provider List React application.
 *
 * This module exports TypeScript types and interfaces used throughout the CardView,
 * provider, and API response layers. It provides strong typing for user, provider,
 * provider, API response, and session context data structures.
 *
 * Exports:
 *   - TabKey: Type for tab keys ("owned" | "shared").
 *   - Provider: Type for provider objects.
 *   - SessionContext: Type for session and authentication context.
 *
 * Usage:
 *   Import these types to ensure type safety and consistency across components and API calls.
 */
import type { SessionContext, Annotations, Tags, User, UserProfile } from "@smarter/common";

// ----------------------------------------------------------------------------
// Provider Definition
// ----------------------------------------------------------------------------
export type ApiKey = {
  id: number;
  name: string;
  manifestUrl: string;
  ready: boolean;
};
export type Provider = {
  id: number;
  hashedId: string;
  createdAt: string;
  updatedAt: string;
  name: string;
  userProfile: UserProfile;
  status: string;
  description: string;
  version: string;
  tags: Tags;
  annotations: Annotations;
  manifestUrl: string;
  ready: boolean;
  isDefault: boolean;
  isActive: boolean;
  isVerified: boolean;
  isFeatured: boolean;
  isDeprecated: boolean;
  isFlagged: boolean;
  isSuspended: boolean;
  baseUrl: string;
  apiKey: ApiKey;
  defaultModel: string | null;
  connectivityTestPath: string | null;
  logo: string | null;
  websiteUrl: string | null;
  ownershipRequested: unknown | null;
  contactEmail: string | null;
  contactEmailVerified: string | null;
  supportEmail: string | null;
  supportEmailVerified: string | null;
  docsUrl: string | null;
  termsOfServiceUrl: string | null;
  privacyPolicyUrl: string | null;
  isOfficialProvider: boolean;
  tosAccepted: boolean;
  tosAcceptedAt: string | null;
  tosAcceptedBy: User | null;
  lastAccessed: string | null;
  expiresAt: string | null;
  rfc1034CompliantName: string | null;
};

// ----------------------------------------------------------------------------
// Component Props Interfaces
// ----------------------------------------------------------------------------
export interface ProviderCardViewProps {
  sessionContext: SessionContext;
  objects: Provider[];
  onRequery: () => void;
}

export interface ProviderListViewProps {
  isLoading: boolean;
  ghostRows: number;
  sessionContext: SessionContext;
  objects: Provider[];
  onRequery: () => void;
}

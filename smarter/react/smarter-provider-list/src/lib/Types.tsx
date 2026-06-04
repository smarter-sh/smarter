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
  description: string;
  version: string;
  tags: Tags;
  annotations: Annotations;
  userProfile: UserProfile;
  lastAccessed: string | null;
  expiresAt: string | null;
  manifestUrl: string;
  ready: boolean;
  apiKey: ApiKey;
  isOfficialProvider: boolean;
  tosAccepted: boolean;
  tosAcceptedBy: User | null;
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

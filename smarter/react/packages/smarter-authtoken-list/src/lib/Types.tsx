/**
 * Central type definitions for the AuthToken List React application.
 *
 * This module exports TypeScript types and interfaces used throughout the DetailView,
 * authtoken, and API response layers. It provides strong typing for user, authtoken,
 * authtoken, API response, and session context data structures.
 *
 * Exports:
 *   - TabKey: Type for tab keys ("owned" | "shared").
 *   - AuthToken: Type for authtoken objects.
 *   - SessionContext: Type for session and authentication context.
 *
 * Usage:
 *   Import these types to ensure type safety and consistency across components and API calls.
 */
import type { SessionContext, Sorting, Annotations, UserProfile, Filtering } from "@smarter/common";

// ----------------------------------------------------------------------------
// AuthToken Definition
// ----------------------------------------------------------------------------
export type AuthToken = {
  id: string; // the token's key_id, a UUID: a token has no integer id
  hashedId: string;
  createdAt: string;
  updatedAt: string;
  name: string;
  description: string;
  version: string;
  tags: string[];
  annotations: Annotations;
  userProfile: UserProfile;
  /** Whether the key may be used: an inactive key is refused. */
  isActive: boolean;
  /** When the key was last used, or null if it never was. */
  lastUsedAt: string | null;
  manifestUrl: string;
  /** The url of the authtoken's detail: its manifest, what it uses, and what uses it. See ResourceDetail. */
  detailUrl: string | null;
  canDelete: boolean; // false if other resources depend on it, or you may not delete it
  ready: boolean;
};

// ----------------------------------------------------------------------------
// Component Props Interfaces
// ----------------------------------------------------------------------------
export interface AuthTokenDetailViewProps {
  sessionContext: SessionContext;
  object: AuthToken;
  onRequery: () => void;
  filtering?: Filtering;
}

export interface AuthTokenListViewProps {
  isLoading: boolean;
  ghostRows: number;
  sessionContext: SessionContext;
  objects: AuthToken[];
  onRequery: () => void;
  sorting?: Sorting;
}

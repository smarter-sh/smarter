/**
 * Central type definitions for the Secret List React application.
 *
 * This module exports TypeScript types and interfaces used throughout the DetailView,
 * secret, and API response layers. It provides strong typing for user, secret,
 * secret, API response, and session context data structures.
 *
 * Exports:
 *   - TabKey: Type for tab keys ("owned" | "shared").
 *   - Secret: Type for secret objects.
 *   - SessionContext: Type for session and authentication context.
 *
 * Usage:
 *   Import these types to ensure type safety and consistency across components and API calls.
 */
import type { SessionContext, Sorting, Annotations, UserProfile, Filtering } from "@smarter/common";

// ----------------------------------------------------------------------------
// Secret Definition
// ----------------------------------------------------------------------------
export type Secret = {
  id: number;
  hashedId: string;
  createdAt: string;
  updatedAt: string;
  name: string;
  description: string;
  version: string;
  tags: string[];
  annotations: Annotations;
  userProfile: UserProfile;
  lastAccessed: string | null;
  expiresAt: string | null;
  manifestUrl: string;
  /** The url of the secret's detail: its manifest, what it uses, and what uses it. See ResourceDetail. */
  detailUrl: string | null;
  canDelete: boolean; // false if other resources depend on it, or you may not delete it
  ready: boolean;
};

// ----------------------------------------------------------------------------
// Component Props Interfaces
// ----------------------------------------------------------------------------
export interface SecretDetailViewProps {
  sessionContext: SessionContext;
  object: Secret;
  onRequery: () => void;
  filtering?: Filtering;
}

export interface SecretListViewProps {
  isLoading: boolean;
  ghostRows: number;
  sessionContext: SessionContext;
  objects: Secret[];
  onRequery: () => void;
  sorting?: Sorting;
}

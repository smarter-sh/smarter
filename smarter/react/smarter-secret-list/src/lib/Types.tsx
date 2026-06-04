/**
 * Central type definitions for the Secret List React application.
 *
 * This module exports TypeScript types and interfaces used throughout the CardView,
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
import type { SessionContext, Annotations, UserProfile } from "@smarter/common";

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
  annotations: Annotations[];
  userProfile: UserProfile;
  lastAccessed: string | null;
  expiresAt: string | null;
  manifestUrl: string;
  ready: boolean;
};

// ----------------------------------------------------------------------------
// Component Props Interfaces
// ----------------------------------------------------------------------------
export interface SecretCardViewProps {
  sessionContext: SessionContext;
  objects: Secret[];
  onRequery: () => void;
}

export interface SecretListViewProps {
  isLoading: boolean;
  ghostRows: number;
  sessionContext: SessionContext;
  objects: Secret[];
  onRequery: () => void;
}

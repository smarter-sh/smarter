/**
 * Central type definitions for the AuthToken List React application.
 *
 * This module exports TypeScript types and interfaces used throughout the CardView,
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
import type { SessionContext, Annotations, UserProfile } from "@smarter/common";

// ----------------------------------------------------------------------------
// AuthToken Definition
// ----------------------------------------------------------------------------
export type AuthToken = {
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
export interface AuthTokenCardViewProps {
  sessionContext: SessionContext;
  objects: AuthToken[];
  onRequery: () => void;
}

export interface AuthTokenListViewProps {
  isLoading: boolean;
  ghostRows: number;
  sessionContext: SessionContext;
  objects: AuthToken[];
  onRequery: () => void;
}

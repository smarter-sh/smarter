/**
 * Central type definitions for the Vectorestore List React application.
 *
 * This module exports TypeScript types and interfaces used throughout the CardView,
 * vectorstore, and API response layers. It provides strong typing for user, vectorstore,
 * vectorstore, API response, and session context data structures.
 *
 * Exports:
 *   - TabKey: Type for tab keys ("owned" | "shared").
 *   - Vectorestore: Type for vectorstore objects.
 *   - SessionContext: Type for session and authentication context.
 *
 * Usage:
 *   Import these types to ensure type safety and consistency across components and API calls.
 */
import type { SessionContext, Annotations, UserProfile } from "@smarter/common";

// ----------------------------------------------------------------------------
// Vectorestore Definition
// ----------------------------------------------------------------------------
export type Vectorestore = {
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
export interface VectorestoreCardViewProps {
  sessionContext: SessionContext;
  objects: Vectorestore[];
  onRequery: () => void;
}

export interface VectorestoreListViewProps {
  isLoading: boolean;
  ghostRows: number;
  sessionContext: SessionContext;
  objects: Vectorestore[];
  onRequery: () => void;
}

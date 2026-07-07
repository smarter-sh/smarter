/**
 * Central type definitions for the Vectorsearch List React application.
 *
 * This module exports TypeScript types and interfaces used throughout the CardView,
 * vectorsearch, and API response layers. It provides strong typing for user, vectorsearch,
 * vectorsearch, API response, and session context data structures.
 *
 * Exports:
 *   - TabKey: Type for tab keys ("owned" | "shared").
 *   - Vectorsearch: Type for vectorsearch objects.
 *   - SessionContext: Type for session and authentication context.
 *
 * Usage:
 *   Import these types to ensure type safety and consistency across components and API calls.
 */
import type { SessionContext, Annotations, Tags, UserProfile } from "@smarter/common";

// ----------------------------------------------------------------------------
// Vectorsearch Definition
// ----------------------------------------------------------------------------

export type VectorsearchSearchType = "similarity" | "similarity_score_threshold" | "mmr";

export type Vectorsearch = {
  id: number;
  hashedId: string;
  createdAt: string;
  updatedAt: string;
  name: string;
  userProfile: UserProfile;
  baseUrl: string;
  description: string;
  version: string;
  tags: Tags;
  annotations: Annotations;
  manifestUrl: string;
  ready: boolean;
  rfc1034CompliantName: string | null;

  vectorstore: string;
  authSecret: string | null;
  searchType: VectorsearchSearchType;
  k: number;
  scoreThreshold: number | null;
  fetchK: number | null;
  lambdaMult: number | null;
  metadataFilter: Record<string, unknown> | null;
  isEnabled: boolean;
};


// ----------------------------------------------------------------------------
// Component Props Interfaces
// ----------------------------------------------------------------------------
export interface VectorsearchCardViewProps {
  sessionContext: SessionContext;
  objects: Vectorsearch[];
  onRequery: () => void;
}

export interface VectorsearchListViewProps {
  isLoading: boolean;
  ghostRows: number;
  sessionContext: SessionContext;
  objects: Vectorsearch[];
  onRequery: () => void;
}

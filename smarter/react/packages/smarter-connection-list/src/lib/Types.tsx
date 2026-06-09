/**
 * Central type definitions for the Connection List React application.
 *
 * This module exports TypeScript types and interfaces used throughout the CardView,
 * connection, and API response layers. It provides strong typing for user, connection,
 * connection, API response, and session context data structures.
 *
 * Exports:
 *   - TabKey: Type for tab keys ("owned" | "shared").
 *   - Connection: Type for connection objects.
 *   - SessionContext: Type for session and authentication context.
 *
 * Usage:
 *   Import these types to ensure type safety and consistency across components and API calls.
 */
import type { SessionContext, Annotations, UserProfile } from "@smarter/common";

// ----------------------------------------------------------------------------
// Connection Definition
// ----------------------------------------------------------------------------
export type Connection = {
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
export interface ConnectionCardViewProps {
  sessionContext: SessionContext;
  objects: Connection[];
  onRequery: () => void;
}

export interface ConnectionListViewProps {
  isLoading: boolean;
  ghostRows: number;
  sessionContext: SessionContext;
  objects: Connection[];
  onRequery: () => void;
}

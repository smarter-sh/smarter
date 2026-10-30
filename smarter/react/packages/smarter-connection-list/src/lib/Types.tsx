/**
 * Central type definitions for the Connection List React application.
 *
 * This module exports TypeScript types and interfaces used throughout the DetailView,
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
import type { SessionContext, Sorting, Annotations, UserProfile, Filtering } from "@smarter/common";

// ----------------------------------------------------------------------------
// Connection Definition
// ----------------------------------------------------------------------------
/** The kinds of connection that the list shows. */
export type ConnectionKind = "SqlConnection" | "ApiConnection";

export type Connection = {
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
  /** The url of the connection's detail: its manifest, what it uses, and what uses it. See ResourceDetail. */
  detailUrl: string | null;
  canDelete: boolean; // false if other resources depend on it, or you may not delete it
  ready: boolean;
  /** The connection's SAM kind. */
  kind: ConnectionKind;
};

// ----------------------------------------------------------------------------
// Component Props Interfaces
// ----------------------------------------------------------------------------
export interface ConnectionDetailViewProps {
  sessionContext: SessionContext;
  object: Connection;
  onRequery: () => void;
  filtering?: Filtering;
}

export interface ConnectionListViewProps {
  isLoading: boolean;
  ghostRows: number;
  sessionContext: SessionContext;
  objects: Connection[];
  onRequery: () => void;
  sorting?: Sorting;
}

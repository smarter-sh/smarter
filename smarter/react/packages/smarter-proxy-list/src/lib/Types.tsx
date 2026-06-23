/**
 * Central type definitions for the Proxy List React application.
 *
 * This module exports TypeScript types and interfaces used throughout the CardView,
 * proxy, and API response layers. It provides strong typing for user, proxy,
 * proxy, API response, and session context data structures.
 *
 * Exports:
 *   - TabKey: Type for tab keys ("owned" | "shared").
 *   - Proxy: Type for proxy objects.
 *   - SessionContext: Type for session and authentication context.
 *
 * Usage:
 *   Import these types to ensure type safety and consistency across components and API calls.
 */
import type { SessionContext, Annotations, UserProfile } from "@smarter/common";

// ----------------------------------------------------------------------------
// Proxy Definition
// ----------------------------------------------------------------------------
export type Proxy = {
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
export interface ProxyCardViewProps {
  sessionContext: SessionContext;
  objects: Proxy[];
  onRequery: () => void;
}

export interface ProxyListViewProps {
  isLoading: boolean;
  ghostRows: number;
  sessionContext: SessionContext;
  objects: Proxy[];
  onRequery: () => void;
}

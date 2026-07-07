/**
 * Central type definitions for the MCPClient List React application.
 *
 * This module exports TypeScript types and interfaces used throughout the CardView,
 * mcpclient, and API response layers. It provides strong typing for user, mcpclient,
 * mcpclient, API response, and session context data structures.
 *
 * Exports:
 *   - TabKey: Type for tab keys ("owned" | "shared").
 *   - MCPClient: Type for mcpclient objects.
 *   - SessionContext: Type for session and authentication context.
 *
 * Usage:
 *   Import these types to ensure type safety and consistency across components and API calls.
 */
import type { SessionContext, Annotations, Tags, UserProfile } from "@smarter/common";

// ----------------------------------------------------------------------------
// MCPClient Definition
// ----------------------------------------------------------------------------
export type MCPTransport = "stdio" | "sse" | "http";

export type MCPAuthType = "none" | "api_key" | "oauth2" | "bearer_token";

export type MCPConnectionStatus =
  | "unconfigured"
  | "connected"
  | "disconnected"
  | "error";

export type MCPClient = {
  id: number;
  hashedId: string;
  createdAt: string;
  updatedAt: string;
  name: string;
  userProfile: UserProfile;
  baseUrl: string;
  status: MCPConnectionStatus;
  description: string;
  version: string;
  tags: Tags;
  annotations: Annotations;
  manifestUrl: string;
  ready: boolean;
  rfc1034CompliantName: string | null;

  // --- connection ---
  transport: MCPTransport;
  command: string;
  config: Record<string, unknown>;

  // --- auth ---
  authType: MCPAuthType;
  credentials: string; // Secret name/slug reference

  // --- capability scope ---
  allowedTools: string[];
  allowedResources: string[];

  // --- lifecycle ---
  isActive: boolean;
  priority: number;

  // --- versioning / provenance ---
  protocolVersion: string;
};


// ----------------------------------------------------------------------------
// Component Props Interfaces
// ----------------------------------------------------------------------------
export interface MCPClientCardViewProps {
  sessionContext: SessionContext;
  objects: MCPClient[];
  onRequery: () => void;
}

export interface MCPClientListViewProps {
  isLoading: boolean;
  ghostRows: number;
  sessionContext: SessionContext;
  objects: MCPClient[];
  onRequery: () => void;
}

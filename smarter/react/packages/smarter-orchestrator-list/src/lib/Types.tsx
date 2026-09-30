/**
 * Central type definitions for the Orchestrator List React application.
 *
 * This module exports TypeScript types and interfaces used throughout the CardView,
 * orchestrator, and API response layers. It provides strong typing for user, orchestrator,
 * orchestrator, API response, and session context data structures.
 *
 * Exports:
 *   - TabKey: Type for tab keys ("owned" | "shared").
 *   - Orchestrator: Type for orchestrator objects.
 *   - SessionContext: Type for session and authentication context.
 *
 * Usage:
 *   Import these types to ensure type safety and consistency across components and API calls.
 */
import type { SessionContext, Annotations, Tags, UserProfile } from "@smarter/common";

// ----------------------------------------------------------------------------
// Orchestrator Definition
// ----------------------------------------------------------------------------

export type OrchestrationStrategy =
  | "sequential"
  | "parallel"
  | "supervisor"
  | "router"
  | "voting"
  | "debate";

export type HarnessRole =
  | "planner"
  | "executor"
  | "critic"
  | "router"
  | "summarizer"
  | "tool_caller";

export type OrchestratorHarness = {
  llmClientName: string;
  role: HarnessRole;
  executionOrder: number;
  isActive: boolean;
  config: Record<string, unknown>;
};

export type Orchestrator = {
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
  strategy: OrchestrationStrategy;
  maxIterations: number;
  isActive: boolean;
  harnesses: OrchestratorHarness[];
};

// ----------------------------------------------------------------------------
// Component Props Interfaces
// ----------------------------------------------------------------------------
export interface OrchestratorCardViewProps {
  sessionContext: SessionContext;
  objects: Orchestrator[];
  onRequery: () => void;
}

export interface OrchestratorListViewProps {
  isLoading: boolean;
  ghostRows: number;
  sessionContext: SessionContext;
  objects: Orchestrator[];
  onRequery: () => void;
}

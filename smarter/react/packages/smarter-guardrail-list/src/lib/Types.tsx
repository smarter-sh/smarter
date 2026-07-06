/**
 * Central type definitions for the Guardrail List React application.
 *
 * This module exports TypeScript types and interfaces used throughout the CardView,
 * guardrail, and API response layers. It provides strong typing for user, guardrail,
 * guardrail, API response, and session context data structures.
 *
 * Exports:
 *   - TabKey: Type for tab keys ("owned" | "shared").
 *   - Guardrail: Type for guardrail objects.
 *   - SessionContext: Type for session and authentication context.
 *
 * Usage:
 *   Import these types to ensure type safety and consistency across components and API calls.
 */
import type { SessionContext, Annotations, Tags, UserProfile } from "@smarter/common";

// ----------------------------------------------------------------------------
// Guardrail Definition
// ----------------------------------------------------------------------------
export type GuardrailType = "input" | "output" | "both";

export type GuardrailCategory =
  | "pii"
  | "jailbreak"
  | "toxicity"
  | "hallucination"
  | "off_topic"
  | "compliance"
  | "custom";

export type MatchStrategy =
  | "regex"
  | "keyword"
  | "semantic"
  | "model"
  | "llm_judge";

export type GuardrailAction =
  | "allow"
  | "flag"
  | "redact"
  | "transform"
  | "block"
  | "escalate";

export type GuardrailConfig = {
  similarity_threshold?: number;
  model_id?: string;
  temperature?: number;
  judge_prompt?: string;
  [key: string]: unknown;
};

export type Guardrail = {
  id: number;
  hashedId: string;
  createdAt: string;
  updatedAt: string;
  name: string;
  userProfile: UserProfile;
  baseUrl: string;
  status: string;
  description: string;
  version: string;
  tags: Tags;
  annotations: Annotations;
  manifestUrl: string;
  ready: boolean;
  rfc1034CompliantName: string | null;

  // --- classification ---
  guardrailType: GuardrailType;
  category: GuardrailCategory;

  // --- detection logic ---
  matchStrategy: MatchStrategy;
  pattern: string;
  config: GuardrailConfig;

  // --- response behavior ---
  action: GuardrailAction;
  severity: number;
  confidenceThreshold: number | null;

  // --- lifecycle ---
  isActive: boolean;
  isBlocking: boolean;
  priority: number;

  // --- versioning / provenance ---
  fallbackMessage: string;
};


// ----------------------------------------------------------------------------
// Component Props Interfaces
// ----------------------------------------------------------------------------
export interface GuardrailCardViewProps {
  sessionContext: SessionContext;
  objects: Guardrail[];
  onRequery: () => void;
}

export interface GuardrailListViewProps {
  isLoading: boolean;
  ghostRows: number;
  sessionContext: SessionContext;
  objects: Guardrail[];
  onRequery: () => void;
}

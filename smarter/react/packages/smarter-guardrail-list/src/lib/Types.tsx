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
export type GuardrailStage = "input" | "output" | "both";

export type GuardrailCategory =
  | "pii"
  | "secrets"
  | "prompt_injection"
  | "jailbreak"
  | "toxicity"
  | "self_harm"
  | "hallucination"
  | "off_topic"
  | "compliance"
  | "formatting"
  | "custom";

export type GuardrailStrategy = "regex" | "keyword" | "detector" | "semantic" | "moderation" | "llm_judge";

export type GuardrailAction = "log" | "flag" | "redact" | "transform" | "block" | "escalate";

export type GuardrailMode = "enforce" | "monitor";

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
  description: string;
  version: string;
  tags: Tags;
  annotations: Annotations;
  manifestUrl: string;
  canDelete: boolean; // false if other resources depend on it, or you may not delete it
  ready: boolean;
  rfc1034CompliantName: string | null;

  // --- classification ---
  stage: GuardrailStage;
  category: GuardrailCategory;

  // --- detection logic ---
  strategy: GuardrailStrategy;
  pattern: string | null;
  config: GuardrailConfig | null;
  threshold: number | null;

  // --- response behavior ---
  action: GuardrailAction;
  replacement: string | null;
  message: string | null;
  severity: number;

  // --- lifecycle ---
  mode: GuardrailMode;
  failClosed: boolean;
  priority: number;
  isActive: boolean;
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

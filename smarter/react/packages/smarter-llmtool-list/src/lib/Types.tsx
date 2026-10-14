/**
 * @file Types.tsx
 * @module llmtool_list/lib/Types
 *
 * Central type definitions for the LLMTool List React application.
 *
 * This module exports TypeScript types and interfaces used throughout the CardView,
 * llmtool, and API response layers. It provides strong typing for user, llmtool,
 * llmtool, API response, and session context data structures.
 *
 * Exports:
 *   - TabKey: Type for tab keys ("user" | "shared").
 *   - LLMTool: Type for LLMTool objects.
 *   - SessionContext: Type for session and authentication context.
 *
 * Usage:
 *   Import these types to ensure type safety and consistency across components and API calls.
 */
import type { SessionContext, Sorting, UserProfile, Tags, Annotations } from "@smarter/common";

export type TabKey = "user" | "shared";

// ----------------------------------------------------------------------------
// LLMTool Definition
// ----------------------------------------------------------------------------
type JsonPrimitive = string | number | boolean | null;
type JsonValue = JsonPrimitive | JsonValue[] | { [key: string]: JsonValue };
type SqlParameterProperty = {
  type: "string" | "number" | "integer" | "boolean";
  description: string;
  enum?: string[];
};

type SqlParameters = {
  type: "object";
  required: string[];
  properties: Record<string, SqlParameterProperty>;
  additionalProperties: boolean;
};

type SqlTestValue = {
  name: string;
  value: string | number | boolean | null;
};

export type StaticData = { [key: string]: JsonValue };
export type ApiData = { [key: string]: JsonValue };
export type SqlData = {
  connection: string;
  description: string;
  parameters: SqlParameters;
  sqlQuery: string;
  testValues: SqlTestValue[];
  limit: number;
};

type LLMToolClass = "static" | "sql" | "api";

type LLMToolSelector = {
  directive: "always" | "search_terms";
  searchTerms: string[] | null;
};

type LLMToolPrompt = {
  provider: string;
  systemRole: string;
  model: string;
  temperature: number;
  maxTokens: number;
};

export type LLMTool = {
  id: number;
  createdAt: string;
  updatedAt: string;
  manifestUrl: string;
  canDelete: boolean; // false if other resources depend on it, or you may not delete it
  name: string;
  kind: string;
  userProfile: UserProfile;
  description: string;
  pluginClass: LLMToolClass;
  version: string;
  annotations: Annotations;
  tags: Tags;
  selector: LLMToolSelector;
  prompt: LLMToolPrompt;
  staticData: StaticData | null;
  sqlData: SqlData | null;
  apiData: ApiData | null;
  ready: boolean;
};

// ----------------------------------------------------------------------------
// Component Props Interfaces
// ----------------------------------------------------------------------------
export interface LLMToolCardViewProps {
  sessionContext: SessionContext;
  objects: LLMTool[];
  onRequery: () => void;
}

export interface LLMToolListViewProps {
  isLoading: boolean;
  ghostRows: number;
  sessionContext: SessionContext;
  objects: LLMTool[];
  onRequery: () => void;
  sorting?: Sorting;
}

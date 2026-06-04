/**
 * @file Types.tsx
 * @module secret_list/lib/Types
 *
 * Central type definitions for the Secret List React application.
 *
 * This module exports TypeScript types and interfaces used throughout the CardView,
 * secret, and API response layers. It provides strong typing for user, secret,
 * secret, API response, and session context data structures.
 *
 * Exports:
 *   - TabKey: Type for tab keys ("user" | "shared").
 *   - Secret: Type for secret objects.
 *   - ApiResponse: Type for API response structure.
 *   - SessionContext: Type for session and authentication context.
 *
 * Usage:
 *   Import these types to ensure type safety and consistency across components and API calls.
 */
import type { SessionContext, UserProfile, Annotations } from "@smarter/common";

export type TabKey = "user" | "shared";

// ----------------------------------------------------------------------------
// Secret Definition
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

type SecretClass = "static" | "sql" | "api";

type SecretSelector = {
  directive: "always" | "search_terms";
  searchTerms: string[] | null;
};

type SecretPrompt = {
  provider: string;
  systemRole: string;
  model: string;
  temperature: number;
  maxTokens: number;
};

export type Secret = {
  id: number;
  createdAt: string;
  updatedAt: string;
  manifestUrl: string;
  name: string;
  kind: string;
  userProfile: UserProfile;
  description: string;
  secretClass: SecretClass;
  version: string;
  annotations: Annotations;
  tags: string[];
  selector: SecretSelector;
  prompt: SecretPrompt;
  staticData: StaticData | null;
  sqlData: SqlData | null;
  apiData: ApiData | null;
  ready: boolean;
};

// ----------------------------------------------------------------------------
// API Response and Session Context Types
// ----------------------------------------------------------------------------
export type ApiResponse = {
  secrets: {
    user: Secret[];
    shared: Secret[];
  };
};

// ----------------------------------------------------------------------------
// Component Props Interfaces
// ----------------------------------------------------------------------------
export interface SecretCardViewProps {
  sessionContext: SessionContext;
  objects: Secret[];
  onRequery: () => void;
}

export interface SecretListViewProps {
  isLoading: boolean;
  ghostRows: number;
  sessionContext: SessionContext;
  objects: Secret[];
  onRequery: () => void;
}

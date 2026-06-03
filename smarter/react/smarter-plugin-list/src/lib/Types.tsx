/**
 * @file Types.tsx
 * @module plugin_list/lib/Types
 *
 * Central type definitions for the Plugin List React application.
 *
 * This module exports TypeScript types and interfaces used throughout the CardView,
 * plugin, and API response layers. It provides strong typing for user, plugin,
 * plugin, API response, and session context data structures.
 *
 * Exports:
 *   - TabKey: Type for tab keys ("user" | "shared").
 *   - Plugin: Type for plugin objects.
 *   - User, UserProfile: Types for user and profile data.
 *   - Plugin: Type for plugin configuration and metadata.
 *   - ApiResponse: Type for API response structure.
 *   - SessionContext: Type for session and authentication context.
 *
 * Usage:
 *   Import these types to ensure type safety and consistency across components and API calls.
 */
import type { SessionContext } from "@smarter/common";

export type TabKey = "user" | "shared";

export type User = {
  username: string;
  email: string;
};
export type UserProfile = {
  user: User;
  account?: {
    accountNumber: string;
  };
};

export type Function = {
  plugin: number;
  createdAt: string;
  id: number;
  name: string;
  updatedAt: string;
};

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

type PluginClass = "static" | "sql" | "api";
type AnnotationValue = string | number | boolean | null;

type PluginSelector = {
  directive: "always" | "search_terms";
  searchTerms: string[] | null;
};

type PluginPrompt = {
  provider: string;
  systemRole: string;
  model: string;
  temperature: number;
  maxTokens: number;
};

export type Plugin = {
  id: number;
  createdAt: string;
  updatedAt: string;
  manifestUrl: string;
  name: string;
  kind: string;
  userProfile: UserProfile;
  description: string;
  pluginClass: PluginClass;
  version: string;
  annotations: Array<Record<string, AnnotationValue>>;
  tags: string[];
  selector: PluginSelector;
  prompt: PluginPrompt;
  staticData: StaticData | null;
  sqlData: SqlData | null;
  apiData: ApiData | null;
  ready: boolean;
};

export type ApiResponse = {
  plugins: {
    user: Plugin[];
    shared: Plugin[];
  };
};

export interface PluginCardViewProps {
  sessionContext: SessionContext;
  objects: Plugin[];
  onRequery: () => void;
}

export interface PluginListViewProps {
  isLoading: boolean;
  ghostRows: number;
  sessionContext: SessionContext;
  objects: Plugin[];
  onRequery: () => void;
}

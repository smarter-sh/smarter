/**
 * Central type definitions for the Prompt List React application.
 *
 * This module exports TypeScript types and interfaces used throughout the CardView,
 * llm_client, and API response layers. It provides strong typing for user, plugin,
 * llm_client, API response, and session context data structures.
 *
 * Exports:
 *   - TabKey: Type for tab keys ("owned" | "shared").
 *   - Plugin: Type for plugin objects.
 *   - User, UserProfile: Types for user and profile data.
 *   - LLMClient: Type for llm_client configuration and metadata.
 *   - SessionContext: Type for session and authentication context.
 *
 * Usage:
 *   Import these types to ensure type safety and consistency across components and API calls.
 */

export type TabKey = "owned" | "shared";

export type Tabs = {
  key: TabKey;
  label: string
}[];


type AnnotationValue = string | number | boolean | null;
export type Annotations = Array<Record<string, AnnotationValue>> | null;
export type Tags = string[] | null;

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

type ListViewBaseProps<TObject, TSessionContext> = {
  isLoading: boolean;
  ghostRows: number;
  sessionContext: TSessionContext;
  objects: TObject[];
  onRequery: () => void;
};

type CardViewBaseProps<TObject, TSessionContext> = {
  sessionContext: TSessionContext;
  objects: TObject[];
  onRequery: () => void;
};

export type SessionContext = {
  ApiUrl: string;
  csrfCookieName: string;
  djangoSessionCookieName: string;
  cookieDomain: string;
  debugMode: boolean;
  smarterClient: string;
  smarterClientVersion: string;
  smarterRequestId: string;
  smarterCapabilities?: string[];
};

export type TabbedViewContext<TObject> = {
  objectType: TObject;
  objectTypeName: string;
  tabs: Tabs;
  ListView: React.ComponentType<ListViewBaseProps<TObject, SessionContext>>;
  CardView: React.ComponentType<CardViewBaseProps<TObject, SessionContext>>;
};

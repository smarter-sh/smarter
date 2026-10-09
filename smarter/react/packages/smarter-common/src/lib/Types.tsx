/**
 * Central type definitions for the Prompt List React application.
 *
 * This module exports TypeScript types and interfaces used throughout the CardView,
 * llmclient, and API response layers. It provides strong typing for user, plugin,
 * llmclient, API response, and session context data structures.
 *
 * Exports:
 *   - TabKey: Type for tab keys ("owned" | "shared").
 *   - Pagination, ListQuery, ListPage: Types for a page of a list api, and the request for it.
 *   - Plugin: Type for plugin objects.
 *   - User, UserProfile: Types for user and profile data.
 *   - LLMClient: Type for llmclient configuration and metadata.
 *   - SessionContext: Type for session and authentication context.
 *
 * Usage:
 *   Import these types to ensure type safety and consistency across components and API calls.
 */

export type TabKey = "owned" | "shared";

export type Tabs = {
  key: TabKey;
  label: string;
}[];

/** The description of a page of a list api's objects, as smarter.lib.django.pagination returns it. */
export type Pagination = {
  page: number;
  pageSize: number;
  numPages: number;
  count: number;
  search: string;
};

/** The page of a list api's objects to request, and the search that they match. All are optional. */
export type ListQuery = {
  page?: number;
  pageSize?: number;
  search?: string;
};

/** A page of a list api's objects. pagination is null when the api does not describe its pages. */
export type ListPage<TObject> = {
  objects: TObject[];
  pagination: Pagination | null;
};

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

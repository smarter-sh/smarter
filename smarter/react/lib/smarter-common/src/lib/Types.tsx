/**
 * @file Types.tsx
 * @module prompt_list/lib/Types
 *
 * Central type definitions for the Prompt List React application.
 *
 * This module exports TypeScript types and interfaces used throughout the CardView,
 * chatbot, and API response layers. It provides strong typing for user, plugin,
 * chatbot, API response, and session context data structures.
 *
 * Exports:
 *   - TabKey: Type for tab keys ("user" | "shared").
 *   - Plugin: Type for plugin objects.
 *   - User, UserProfile: Types for user and profile data.
 *   - Chatbot: Type for chatbot configuration and metadata.
 *   - ApiResponse: Type for API response structure.
 *   - SessionContext: Type for session and authentication context.
 *
 * Usage:
 *   Import these types to ensure type safety and consistency across components and API calls.
 */

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

export type ApiResponse<TObject> = {
  chatbots: {
    user: UserProfile[];
    shared: TObject[];
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

export type SessionContext<TObject> = {
  ApiUrl: string;
  csrfCookieName: string;
  djangoSessionCookieName: string;
  cookieDomain: string;
  objectType: TObject;
  objectTypeName: string;
  ListView: React.ComponentType<ListViewBaseProps<TObject, SessionContext<TObject>>>;
  CardView: React.ComponentType<CardViewBaseProps<TObject, SessionContext<TObject>>>;
};

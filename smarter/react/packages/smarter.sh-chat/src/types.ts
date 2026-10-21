/**
 * Types for Smarter Chat: its props, its messages, and the data that the Smarter api returns.
 *
 * The api's types are generated from the contract's JSON Schema (contract/chat-contract.schema.json,
 * which the Smarter backend generates from smarter.apps.prompt.contract.models) into contract.gen.ts.
 * They describe the fields that Smarter Chat reads. The api returns more, which onConfig passes on as is.
 */
import type { ReactNode } from "react";

import type * as Contract from "./contract.gen";
import type { MessageDirection, SenderRole } from "./lib/enums";

export type { Contract };

/** A message in the format of the OpenAI chat completion api, as the backend stores and returns them. */
export type ApiMessage = Contract.PromptChatApiMessage;

/** A message in the chat thread. */
export interface ChatMessage {
  /** The message's text, as html, for display. */
  message: string;
  /** The message's text, as sent to the api. */
  content: ApiMessage["content"];
  direction: MessageDirection;
  sender: SenderRole | string;
  sentTime: string;
  /** false for messages that are part of the thread, but never displayed, e.g. an assistant's tool calls. */
  display: boolean;
  /** The api's original message, whose other fields (e.g. tool_calls) are sent back to the api. */
  originalMessage?: ApiMessage;
}

/** The LLMClient, in the configuration. */
export type LLMClientConfig = Contract.PromptChatApiLLMClient;

/** @deprecated Use LLMClientConfig. Version 2 of the contract calls the LLMClient "llmclient", not "chatbot". */
export type ChatbotConfig = LLMClientConfig;

/** The chat session's history. Only chat_history is returned to clients that can't read the LLMClient. */
export type ChatHistory = Contract.PromptChatApiHistory;

/** The LLMClient's state. */
export type ChatMetaData = Contract.PromptChatApiMetaData;

/**
 * The LLMClient's configuration, from its config api, in version 2 of the contract. A version 1
 * configuration, from an older Smarter platform, is converted to it. See lib/api.ts.
 */
export type ChatConfig = Contract.PromptChatApiConfig & {
  /**
   * @deprecated Use llmclient. Version 2 of the contract calls the LLMClient "llmclient". This is a
   * read-only alias of it, for code written for version 1, which is not enumerable, so it is never
   * serialized or displayed.
   */
  readonly chatbot: LLMClientConfig;
};

/** A cookie that Smarter Chat reads, and possibly sets. */
export interface CookieMeta {
  name: string;
  /** milliseconds, for cookies that Smarter Chat sets. */
  expiration: number | null;
  /** The domain that the page's hostname must be in for the cookie to be read. */
  domain: string;
  /** A value to use instead of the cookie's. */
  value: string | null;
  /** The path that Smarter Chat sets the cookie for. Empty or missing means the page's path. */
  path?: string | null;
}

export interface ChatCookies {
  csrfCookie: CookieMeta;
  sessionCookie: CookieMeta;
  debugCookie: CookieMeta;
}

/** Who is calling the api, sent as the X-Smarter-* request headers. */
export interface ClientContext {
  smarterClient: string;
  smarterClientVersion: string;
  smarterRequestId?: string;
  /** An optional Smarter api key, sent as "Authorization: Token <apiKey>". */
  apiKey?: string | null;
}

export interface SmarterChatProps {
  /** The url of the LLMClient's api. example: https://smarter.3141-5926-5359.beta.api.smarter.sh/ */
  apiUrl: string;
  /** An optional Smarter api key, for LLMClients that require authentication. */
  apiKey?: string | null;
  /**
   * Show the Sandbox / Production mode switch, which shows and hides the thread's metadata messages (Smarter's
   * system, tool and meta data messages), and start in sandbox mode.
   */
  toggleMetadata?: boolean;
  /** The name of Django's CSRF cookie. */
  csrfCookieName?: string;
  /** Django's CSRF token, when the page cannot read the CSRF cookie. */
  csrftoken?: string | null;
  /** The name of the cookie in which Smarter Chat saves the debug mode. */
  debugCookieName?: string;
  debugCookieExpiration?: number;
  /** Log to the browser console. */
  debugMode?: boolean;
  /** The name of the cookie in which Smarter Chat saves the chat session's key. */
  sessionCookieName?: string;
  sessionCookieExpiration?: number;
  /**
   * The path of the session and debug cookies. By default, the page's path, so that each page has its own chat
   * session. "/" keeps one chat session as the visitor moves from page to page of a website.
   */
  cookiePath?: string | null;
  /** @deprecated Not used. Django's session cookie is sent with each request, as is. */
  authSessionCookieName?: string;
  /** The domain whose cookies Smarter Chat reads. example: platform.smarter.sh */
  cookieDomain?: string;
  /** A unique id of the page request, sent as the X-Smarter-RequestId header. */
  smarterRequestId?: string;
  /**
   * Display the progress of a running prompt, e.g. its tool calls, which the prompt api streams as
   * Server-Sent Events. Servers that don't stream answer as before.
   */
  streamProgress?: boolean;
  /**
   * The language of the chat's own text, e.g. its buttons' labels, as a language tag: "en", "es" or "fr", or a
   * regional variant of one, e.g. "es-MX", which gets its generic language. By default, the page's (the lang
   * attribute of its <html> element), or else the browser's. Other languages get English.
   */
  language?: string | null;
  /**
   * Fetch the configuration's diagnostic parts too, e.g. the chat session's tool calls, which are costly for the
   * platform to build, and fetch them again after each prompt. The platform sends them only to a user who may read
   * the LLMClient. onConfig receives them.
   */
  verbose?: boolean;
  /** Reload the configuration when this changes, e.g. after the page changed the LLMClient's manifest. */
  reloadKey?: number | string;
  /** Buttons that the page adds to the chat's header, after its own. See HeaderButton. */
  headerActions?: ReactNode;
  /** Called with the configuration each time it loads: at the start of a chat, and with verbose, after each prompt. */
  onConfig?: (config: ChatConfig) => void;
  /** Called when the user starts a new chat, whose session has a new key. */
  onNewChat?: () => void;
  /** Called with whether the chat is in sandbox mode (true) or production mode, when it starts and when it changes. */
  onModeChange?: (sandbox: boolean) => void;
}

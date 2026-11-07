/** The types of the Prompt Engineer's Workbench. */
import type { SessionContext } from "@smarter/common";

/**
 * The workbench's configuration. The single-page console (@smarter/console) builds it from the LLMClient's hashed id
 * and its session; the development page (main.tsx) uses the fixtures'.
 */
export interface WorkbenchConfig {
  /** The LLMClient in the platform api, /api/v1/llm-clients/<hashed id>/, to which the chat appends config/. */
  apiUrl: string;
  /** Show the chat's Sandbox / Production mode switch, and start in sandbox mode. */
  toggleMetadata: boolean;
  csrfCookieName: string;
  /** The name of the cookie of the chat session's key. */
  sessionCookieName: string;
  cookieDomain: string;
  debugMode: boolean;
  smarterRequestId: string;
  /** The user's server log stream. Without it, the Console has no Server Logs tab. */
  logStreamUrl: string | null;
  /** The LLMClient's manifest, as JSON. Without it, the Console has no Manifest tab. */
  manifestUrl: string | null;
  /** The LLMClient's architecture, the tree of the SAM resources that it is built from. Without it, the Console has no Architecture tab. */
  architectureUrl: string | null;
  /** The LLMClient's deployment page's data. Without it, the Console has no Deployment tab. */
  deploymentUrl: string | null;
  /** The LLM Clients list, where the workbench goes after its LLMClient is deleted. */
  llmclientListUrl: string;
  /** Go to a page of the host, e.g. the router's navigate. Without it, the browser loads the page. */
  navigate?: (url: string) => void;
  /** The cli api's urls, with which the manifest editor saves, validates and deletes the manifest. */
  applyApiUrl: string;
  validateApiUrl: string;
  deleteApiUrl: string;
  kindPlaceholder: string;
  /** Django's session and CSRF cookies, and the request headers, for the Console's own requests. */
  session: SessionContext;
}

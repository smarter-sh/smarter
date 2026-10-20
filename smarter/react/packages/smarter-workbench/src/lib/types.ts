/** The types of the Prompt Engineer's Workbench. */
import type { SessionContext } from "@smarter/common";

/**
 * The workbench's configuration, from its root element's attributes, which Django renders: see
 * templates/react/workbench.html, and smarter.apps.prompt.views.detailviews.prompt_workbench_view.PromptWorkbenchView.
 */
export interface WorkbenchConfig {
  /** The LLMClient's api, for the chat: its sandbox url. */
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
  /** The cli api's urls, with which the manifest editor saves, validates and deletes the manifest. */
  applyApiUrl: string;
  validateApiUrl: string;
  deleteApiUrl: string;
  kindPlaceholder: string;
  /** Django's session and CSRF cookies, and the request headers, for the Console's own requests. */
  session: SessionContext;
}

/**
 * The Prompt Engineer's Workbench's configuration, from the LLMClient's hashed id and the console's session: the urls
 * that Django passed it until it moved here. See routes/WorkbenchPage, and smarter.apps.prompt.api.web.urls.
 */
import type { WorkbenchConfig } from "@smarter/workbench";

import type { ConsoleSession } from "@/contract.gen";
import { djangoSessionContext, requestId } from "@/lib/djangoSession";
import { KIND_PLACEHOLDER, manifestEditorUrls } from "@/lib/manifestPages";
import { toolUrls } from "@/lib/tools";

/** The workbench's route. */
export const WORKBENCH_PATH = "/workbench/llm-clients/:id/prompt";

/** The LLM Clients list, where the workbench goes after its LLMClient is deleted. */
export const LLMCLIENT_LIST_PATH = "/workbench";

/** The cookie of the chat session's key: smarter.common.const.SMARTER_CHAT_SESSION_KEY_NAME. */
export const CHAT_SESSION_COOKIE_NAME = "session_key";

/** The LLMClient's record locator, for the resource api, which decides whether the user may open its workbench. */
export function llmclientLocator(hashedId: string): string {
  return `llmclient-${hashedId}`;
}

/**
 * The workbench's configuration.
 *
 * @param session - The console's session.
 * @param hashedId - The LLMClient's hashed id, from the route.
 * @param navigate - The router's navigate, with which the workbench leaves for the list after a delete.
 * @returns The configuration, with every tab, and the Server Logs tab while the session's serverLogs is on.
 */
export function workbenchConfig(
  session: ConsoleSession,
  hashedId: string,
  navigate: (url: string) => void,
): WorkbenchConfig {
  const id = encodeURIComponent(hashedId);
  const webApi = `/api/web/prompt/llm-clients/${id}/`;
  const sessionContext = djangoSessionContext(session, manifestEditorUrls.apply, ["custom"]);
  return {
    apiUrl: `/api/v1/llm-clients/${id}/`,
    toggleMetadata: true,
    csrfCookieName: session.cookies.csrfCookieName,
    sessionCookieName: CHAT_SESSION_COOKIE_NAME,
    cookieDomain: sessionContext.cookieDomain,
    debugMode: session.flags.reactDebugMode,
    smarterRequestId: requestId(),
    logStreamUrl: session.flags.serverLogs ? toolUrls.logStream : null,
    manifestUrl: `${webApi}manifest/`,
    architectureUrl: `${webApi}architecture/`,
    deploymentUrl: `${webApi}deployment/`,
    llmclientListUrl: LLMCLIENT_LIST_PATH,
    navigate,
    applyApiUrl: manifestEditorUrls.apply,
    validateApiUrl: manifestEditorUrls.validate,
    deleteApiUrl: manifestEditorUrls.delete,
    kindPlaceholder: KIND_PLACEHOLDER,
    session: sessionContext,
  };
}

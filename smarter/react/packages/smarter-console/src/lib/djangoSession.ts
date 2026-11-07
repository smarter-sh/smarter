/**
 * The SessionContext of @smarter/common, from the console's session: what the backend's React apps, e.g. the user
 * menu and the dashboard, need for their requests, which they read from their template's attributes on the pages
 * that the backend still renders.
 */
import type { SessionContext } from "@smarter/common";

import type { ConsoleSession } from "@/contract.gen";
import { projectName, projectVersion } from "@/lib/const";

/** A new id for a page's requests, which the backend logs: 32 hex digits. */
export function requestId(): string {
  return crypto.randomUUID().replaceAll("-", "");
}

/**
 * The SessionContext of an app's requests.
 *
 * @param session - The console's session.
 * @param apiUrl - The app's main api url.
 * @param capabilities - The X-Smarter-Capabilities that the app sends, if any.
 * @returns The context, with a new request id.
 */
export function djangoSessionContext(session: ConsoleSession, apiUrl: string, capabilities?: string[]): SessionContext {
  const { cookies, flags } = session;
  return {
    ApiUrl: apiUrl,
    csrfCookieName: cookies.csrfCookieName,
    djangoSessionCookieName: cookies.sessionCookieName,
    cookieDomain: cookies.cookieDomain || window.location.hostname,
    debugMode: flags.reactDebugMode,
    smarterClient: projectName,
    smarterClientVersion: projectVersion,
    smarterRequestId: requestId(),
    smarterCapabilities: capabilities,
  };
}

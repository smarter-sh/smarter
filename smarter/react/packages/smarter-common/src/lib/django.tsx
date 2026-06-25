/**
 * Sends a POST request to the Smarter Django backend with CSRF and session authentication.
 *
 * @param requestJson - The JSON string body to send in the request.
 * @param url - The URL to send the POST request to.
 * @param sessionContext - The session context containing API URL, CSRF token, and session cookie information.
 * @returns A `Promise<Response>` from the Fetch API.
 */
import { loggerPrefix } from "./const";
import { getCookie } from "./cookie";
import type { SessionContext } from "./Types";

export default async function fetchDjangoUrl(
  sessionContext: SessionContext,
  url: string,
  requestJson: string,
) {
  const applicationJson = "application/json";
  const djangoSessionTokenValue =
    getCookie({ name: sessionContext.djangoSessionCookieName, expiration: null, domain: sessionContext.cookieDomain, value: null }, "") || "";
  const csrftokenValue =
    getCookie({ name: sessionContext.csrfCookieName, expiration: null, domain: sessionContext.cookieDomain, value: null }, "") || "";

  const capabilities = sessionContext.smarterCapabilities ? sessionContext.smarterCapabilities.join(",") : "listview,cardview";

  /*
   * note that any custom headers that are added here must also be added to the Django
   * backend's CORS_ALLOW_HEADERS setting in smarter.settings.base.py.
   */
  const requestHeaders = {
    Accept: applicationJson,
    Authorization: `Bearer ${djangoSessionTokenValue}`,
    "Content-Type": applicationJson,
    "X-CSRFToken": csrftokenValue,
    "X-Smarter-Client": sessionContext.smarterClient,
    "X-Smarter-Client-Version": sessionContext.smarterClientVersion,
    "X-Smarter-Client-Type": "react",
    "X-Smarter-Request-ID": sessionContext.smarterRequestId,
    "X-Smarter-Capabilities": capabilities,
  };

  console.debug(`${loggerPrefix} fetchDjangoUrl() Sending POST request to ${url}`, "with headers:", requestHeaders, "with body:", requestJson);

  const res = await fetch(url, {
    method: "POST",
    headers: requestHeaders,
    body: requestJson,
  });

  console.debug(`${loggerPrefix} fetchDjangoUrl() Received response from ${url}:`, res);

  return res;
}

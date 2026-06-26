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
  const csrftokenValue =
    getCookie({ name: sessionContext.csrfCookieName, domain: sessionContext.cookieDomain });
  const capabilities = sessionContext.smarterCapabilities ? sessionContext.smarterCapabilities.join(",") : "listview,cardview";

  if (!csrftokenValue) {
    console.error(`${loggerPrefix} fetchDjangoUrl() No CSRF token found for cookie name ${sessionContext.csrfCookieName} in domain ${sessionContext.cookieDomain}.`);
  }

  /*
   * note that any custom headers that are added here must also be added to the Django
   * backend's CORS_ALLOW_HEADERS setting in smarter.settings.base.py.
   */
  const requestHeaders = {
    Accept: applicationJson,
    "X-CSRFToken": csrftokenValue!,
    "Content-Type": applicationJson,
    "X-Smarter-Client": sessionContext.smarterClient,
    "X-Smarter-ClientVersion": sessionContext.smarterClientVersion,
    "X-Smarter-ClientType": "react",
    "X-Smarter-RequestId": sessionContext.smarterRequestId,
    "X-Smarter-Capabilities": capabilities,
  };

  console.debug(`${loggerPrefix} fetchDjangoUrl() Sending POST request to ${url}`, "with headers:", requestHeaders, "with body:", requestJson);

  const res = await fetch(url, {
    method: "POST",
    credentials: "include",
    headers: requestHeaders,
    body: requestJson,
  });

  console.debug(`${loggerPrefix} fetchDjangoUrl() Received response from ${url}:`, res);

  return res;
}

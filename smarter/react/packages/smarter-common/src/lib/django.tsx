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
  const userAgent = "SmarterChat/1.0";
  const applicationJson = "application/json";
  const authToken =
    getCookie({ name: sessionContext.djangoSessionCookieName, expiration: null, domain: sessionContext.cookieDomain, value: null }, "") || "";
  const csrftokenFromCookie =
    getCookie({ name: sessionContext.csrfCookieName, expiration: null, domain: sessionContext.cookieDomain, value: null }, "") || "";
  const requestHeaders = {
    Accept: applicationJson,
    "Content-Type": applicationJson,
    "X-CSRFToken": csrftokenFromCookie,
    Origin: window.location.origin,
    Authorization: `Bearer ${authToken}`,
    "User-Agent": userAgent,
  };

  console.debug(`${loggerPrefix} fetchDjangoUrl() Sending POST request to ${url}`, "with body:", requestJson);

  const res = await fetch(url, {
    method: "POST",
    headers: requestHeaders,
    body: requestJson,
  });

  console.debug(`${loggerPrefix} fetchDjangoUrl() Received response from ${url}:`, res);

  return res;
}

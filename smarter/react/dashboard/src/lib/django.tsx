
import { loggerPrefix } from "@/const";
import getCookie from "./cookie";

/**
 * Sends a POST request to the Smarter Django backend with CSRF and session authentication.
 *
 * @param requestJson - The JSON string body to send in the request.
 * @param url - The Django endpoint URL to POST to.
 * @param djangoSessionCookieName - Name of the Django session cookie used as the Bearer token.
 * @param csrfCookieName - Name of the CSRF cookie to validate against `csrfToken`.
 * @param cookieDomain - The domain used when reading cookies.
 * @returns A `Promise<Response>` from the Fetch API.
 */
export default async function fetchDjangoUrl(requestJson: string, url: string, djangoSessionCookieName: string, csrfCookieName: string, cookieDomain: string) {

    const userAgent = "SmarterChat/1.0";
    const applicationJson = "application/json";
    const authToken = getCookie({ name: djangoSessionCookieName, expiration: null, domain: cookieDomain, value: null }, "") || "";
    const csrftokenFromCookie = getCookie({ name: csrfCookieName, expiration: null, domain: cookieDomain, value: null }, "") || "";
    const requestHeaders = {
      "Accept": applicationJson,
      "Content-Type": applicationJson,
      "X-CSRFToken": csrftokenFromCookie,
      "Origin": window.location.origin,
      "Authorization": `Bearer ${authToken}`,
      "User-Agent": userAgent,
    };

    console.debug(loggerPrefix, `Sending POST request to ${url}`, "with body:", requestJson);

    const res = await fetch(url, {
      method: "POST",
      headers: requestHeaders,
      body: requestJson,
    });

    console.debug(loggerPrefix, `Received response from ${url}:`, res);

    return res;
  };

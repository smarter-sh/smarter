/**
 * The console's calls to the backend's web console api, ``/api/web/``.
 *
 * Every call carries the browser's Django session cookie. A POST also carries the CSRF token, read from the
 * cookie that GET /api/web/session/ sets, in the X-CSRFToken header.
 */
import { getCookie } from "@smarter/common";

import type { ConsoleCookies } from "@/contract.gen";
import { projectName, projectVersion } from "@/lib/const";

/** A response that wasn't 2xx. */
export class ApiError extends Error {
  readonly status: number;
  readonly body: unknown;

  constructor(url: string, status: number, body: unknown) {
    super(`${url} answered ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

/** The headers that every call sends. */
function smarterHeaders(): Record<string, string> {
  return {
    Accept: "application/json",
    "X-Smarter-Client": projectName,
    "X-Smarter-ClientVersion": projectVersion,
    "X-Smarter-ClientType": "react",
    "X-Smarter-RequestId": crypto.randomUUID().replaceAll("-", ""),
  };
}

/** The body of a response, as JSON when it is JSON. */
async function readBody(response: Response): Promise<unknown> {
  const contentType = response.headers.get("Content-Type") ?? "";
  if (contentType.includes("application/json")) {
    return response.json();
  }
  return response.text();
}

/** The parsed body of a 2xx response, or an ApiError. */
async function handle<T>(url: string, response: Response): Promise<T> {
  const body = await readBody(response);
  if (!response.ok) {
    throw new ApiError(url, response.status, body);
  }
  return body as T;
}

/** GET a JSON endpoint. */
export async function getJson<T>(url: string): Promise<T> {
  const response = await fetch(url, { method: "GET", credentials: "include", headers: smarterHeaders() });
  return handle<T>(url, response);
}

/**
 * POST JSON to an endpoint, with the CSRF token.
 *
 * @param url - The endpoint.
 * @param body - The request's body, sent as JSON.
 * @param cookies - The cookie names and domain, from the session.
 */
export async function postJson<T>(url: string, body: unknown, cookies: ConsoleCookies): Promise<T> {
  const csrfToken = getCookie({
    name: cookies.csrfCookieName,
    domain: cookies.cookieDomain || window.location.hostname,
  });
  const headers = {
    ...smarterHeaders(),
    "Content-Type": "application/json",
    "X-CSRFToken": csrfToken ?? "",
  };
  const response = await fetch(url, { method: "POST", credentials: "include", headers, body: JSON.stringify(body) });
  return handle<T>(url, response);
}

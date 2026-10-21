/**
 * Cookie management for Smarter Chat: the Django CSRF cookie, which it reads, and the chat
 * session and debug cookies, which it sets for the page's path, so that each LLMClient's
 * workbench has its own chat session, or for the path that the cookie names, e.g. "/" for a chat
 * that follows the visitor across a website.
 */
import type { CookieMeta } from "../types";

/**
 * Whether the page's hostname is in a cookie's domain. Django's cookie domain settings may
 * include a port (localhost:9357) or a leading dot (.smarter.sh), and may be empty or "None",
 * which means the page's own domain.
 */
export function inCookieDomain(hostname: string, domain: string | null | undefined): boolean {
  const cookieDomain = (domain || "").trim().split(":")[0].replace(/^\./, "");
  if (!cookieDomain || cookieDomain === "None") {
    return true;
  }
  return hostname === cookieDomain || hostname.endsWith(`.${cookieDomain}`);
}

/** The cookie's value: its preset value, else the browser's cookie, else defaultValue. */
export function getCookie(cookie: CookieMeta, defaultValue: string | null = null): string | null {
  if (cookie.value !== null && cookie.value !== undefined && cookie.value !== "") {
    return cookie.value;
  }
  if (!inCookieDomain(window.location.hostname, cookie.domain) || !document.cookie) {
    return defaultValue;
  }
  for (const item of document.cookie.split(";")) {
    const thisCookie = item.trim();
    if (thisCookie.startsWith(`${cookie.name}=`)) {
      return decodeURIComponent(thisCookie.substring(cookie.name.length + 1)) || defaultValue;
    }
  }
  return defaultValue;
}

/** Sets the cookie for its path (by default, the page's), or deletes it when value is empty. */
export function setCookie(cookie: CookieMeta, value: string | boolean | null | undefined): void {
  const path = cookie.path || window.location.pathname;
  if (value === null || value === undefined || value === "") {
    document.cookie = `${cookie.name}=; path=${path}; SameSite=Lax; expires=${new Date(0).toUTCString()}`;
    return;
  }
  const expires = new Date(Date.now() + (cookie.expiration ?? 0)).toUTCString();
  document.cookie = `${cookie.name}=${encodeURIComponent(String(value))}; path=${path}; SameSite=Lax; expires=${expires}`;
}

export function cookieMetaFactory(
  name: string,
  expiration: number | null,
  domain: string | undefined,
  value: string | null = null,
  path: string | null = null,
): CookieMeta {
  return { name, expiration, domain: domain ?? "", value, path };
}

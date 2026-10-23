/**
 * Tabbed list cache utilities.
 *
 * Stores each page of a list api's objects, with its pagination, in localStorage, so that a list
 * paints at once, from what it last showed, while it asks the api for a fresh page: on a return
 * visit, in a new browser tab, and when paging or sorting back to a page seen before.
 *
 * - A key is scoped by the session (see sessionScope), the api url, the tab, and the page's page
 *   number, ordering and filter. Searches are not cached.
 * - Entries expire after a week, and only the most recent MAX_ENTRIES are kept.
 * - Every storage access is guarded: a private window, blocked site data or a full quota is a cache
 *   miss, never an error.
 */
import { loggerPrefix } from "./const";
import { packageName } from "./const";
import type { Pagination, SessionContext } from "./Types";
import { getCookie } from "./cookie";

const CACHE_PREFIX = `${packageName}_objects_v2`;
const CACHE_TTL_MS = 7 * 24 * 60 * 60 * 1000; // 1 week

/** The most entries kept: the oldest beyond it are removed on each write. */
export const MAX_ENTRIES = 100;

type CacheEntry<T> = {
  ts: number;
  objects: T[];
  pagination: Pagination | null;
};

/** A cached page of a list: its objects, and its pagination, if the api described it. */
export type CachedPage<T> = {
  objects: T[];
  pagination: Pagination | null;
};

/** The page of a list that a key names. A search is never cached, so it has no part in the key. */
export type CacheQuery = {
  page?: number;
  ordering?: string;
  filter?: string;
};

/** A 32-bit FNV-1a hash, in hex, so that a key names a session without holding its token. */
const fnv1a = (text: string): string => {
  let hash = 0x811c9dc5;
  for (let i = 0; i < text.length; i++) {
    hash ^= text.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193);
  }
  return (hash >>> 0).toString(16);
};

/**
 * Returns a short name of the browser's session, for scoping cache keys.
 *
 * It is a hash of the CSRF cookie, which Django rotates at every login. So pages cached in
 * localStorage, which outlives the session, are never shown to the next user who logs in, on the
 * same browser.
 *
 * @param sessionContext The list's session context, which names the CSRF cookie.
 * @returns The session's scope, or "" when the CSRF cookie can't be read.
 */
export const sessionScope = (sessionContext: Pick<SessionContext, "csrfCookieName" | "cookieDomain">): string => {
  const token = getCookie({ name: sessionContext.csrfCookieName, domain: sessionContext.cookieDomain });
  return token ? fnv1a(token) : "";
};

/**
 * Builds a stable localStorage key for a page of a list api's tab.
 *
 * @param apiUrl Base API URL used to scope cache entries by backend.
 * @param slug Tab or list identifier to isolate cached objects per view.
 * @param query The page's page number, ordering and filter. The first page, in the default order, unfiltered, if omitted.
 * @param scope The session's scope, from sessionScope().
 * @returns A deterministic localStorage key.
 */
export const makeCacheKey = (apiUrl: string, slug: string, query: CacheQuery = {}, scope: string = "") => {
  const page = query.page ?? 1;
  return `${CACHE_PREFIX}:${scope}:${apiUrl}${slug}?page=${page}&ordering=${query.ordering ?? ""}&filter=${query.filter ?? ""}`;
};

const storage = (): Storage | null => {
  try {
    return window.localStorage;
  } catch {
    return null;
  }
};

/** The keys of this cache's entries, in localStorage. */
const cacheKeys = (store: Storage): string[] => {
  const keys: string[] = [];
  for (let i = 0; i < store.length; i++) {
    const key = store.key(i);
    if (key && key.startsWith(`${CACHE_PREFIX}:`)) keys.push(key);
  }
  return keys;
};

const parse = <T,>(raw: string | null): CacheEntry<T> | null => {
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as CacheEntry<T>;
    if (!parsed || typeof parsed.ts !== "number" || !Array.isArray(parsed.objects)) return null;
    return parsed;
  } catch {
    return null;
  }
};

/**
 * Removes this cache's expired entries, and its oldest beyond MAX_ENTRIES.
 *
 * @returns `void`. Storage errors are ignored.
 */
export const pruneCache = () => {
  const store = storage();
  if (!store) return;
  try {
    const now = Date.now();
    const live: { key: string; ts: number }[] = [];
    cacheKeys(store).forEach((key) => {
      const entry = parse(store.getItem(key));
      if (!entry || now - entry.ts > CACHE_TTL_MS) store.removeItem(key);
      else live.push({ key, ts: entry.ts });
    });
    live
      .sort((a, b) => b.ts - a.ts)
      .slice(MAX_ENTRIES)
      .forEach(({ key }) => store.removeItem(key));
  } catch {
    // ignore storage errors
  }
};

/**
 * Reads and validates a cached page.
 *
 * Returns null for missing, invalid, or expired entries and removes expired
 * data to keep storage clean.
 *
 * @param key Fully qualified localStorage cache key.
 * @returns The cached page when present and valid; otherwise `null`.
 * @throws No exceptions are propagated. JSON parse errors, storage access
 * failures, and other runtime errors are caught and treated as a cache miss.
 */
export const readCache = <T,>(key: string): CachedPage<T> | null => {
  const store = storage();
  if (!store) return null;
  try {
    const entry = parse<T>(store.getItem(key));
    if (!entry) {
      console.debug(`${loggerPrefix} readCache() cache miss for`, key);
      return null;
    }
    if (Date.now() - entry.ts > CACHE_TTL_MS) {
      console.debug(`${loggerPrefix} readCache() cache expired for`, key);
      store.removeItem(key);
      return null;
    }
    console.debug(`${loggerPrefix} readCache() cache hit for`, key);
    return { objects: entry.objects, pagination: entry.pagination ?? null };
  } catch {
    return null;
  }
};

/**
 * Persists a page of objects to localStorage with a write timestamp, then prunes the cache.
 *
 * @param key Fully qualified localStorage cache key.
 * @param objects The page's objects.
 * @param pagination The page's pagination, as the list api described it.
 * @returns `void`.
 * @throws No exceptions are propagated. Storage write failures (for
 * example quota exceeded or private mode restrictions) are caught and ignored.
 */
export const writeCache = <T,>(key: string, objects: T[], pagination: Pagination | null = null) => {
  const store = storage();
  if (!store) return;
  try {
    console.debug(
      `${loggerPrefix} writeCache() writing localStorage cache for`,
      key,
      "with",
      objects.length,
      "objects",
    );
    const payload: CacheEntry<T> = { ts: Date.now(), objects, pagination };
    store.setItem(key, JSON.stringify(payload));
  } catch {
    // ignore quota/private-mode errors
  }
  pruneCache();
};

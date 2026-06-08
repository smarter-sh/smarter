/**
 * Tabbed list cache utilities.
 *
 * Stores plugin objects in sessionStorage using a key scoped by API URL and slug,
 * with a one-week TTL and automatic cleanup of expired entries.
 */
import { packageName, packageVersion } from "../../lib/const";

const CACHE_PREFIX = `${packageName}_v${packageVersion}_objects_v1`;
const CACHE_TTL_MS = 7 * 24 * 60 * 60 * 1000; // 1 week

type CacheEntry = {
  ts: number;
  objects: any[];
};

/**
 * Builds a stable sessionStorage key for a specific API endpoint and tab slug.
 *
 * @param apiUrl Base API URL used to scope cache entries by backend.
 * @param slug Tab or list identifier to isolate cached objects per view.
 * @returns A deterministic sessionStorage key.
 * @throws This function does not throw under normal operation.
 */
export const makeCacheKey = (apiUrl: string, slug: string) => {
  return `${CACHE_PREFIX}:${apiUrl}${slug}`;
};

/**
 * Reads and validates cached llm_client objects.
 *
 * Returns null for missing, invalid, or expired entries and removes expired
 * data to keep storage clean.
 *
 * @param key Fully qualified sessionStorage cache key.
 * @returns The cached llm_client array when present and valid; otherwise `null`.
 * @throws No exceptions are propagated. JSON parse errors, sessionStorage access
 * failures, and other runtime errors are caught and treated as a cache miss.
 */
export const readCache = (key: string): any[] | null => {
  try {
    const raw = sessionStorage.getItem(key);
    if (!raw) return null;

    const parsed = JSON.parse(raw) as CacheEntry;
    if (!parsed || typeof parsed.ts !== "number" || !Array.isArray(parsed.objects)) return null;

    if (Date.now() - parsed.ts > CACHE_TTL_MS) {
      sessionStorage.removeItem(key);
      return null;
    }
    console.debug("cache hit for", key);
    return parsed.objects;
  } catch {
    return null;
  }
};

/**
 * Persists llm_client objects to sessionStorage with a write timestamp.
 *
 * @param key Fully qualified sessionStorage cache key.
 * @param objects LLMClient objects to cache for subsequent reads.
 * @returns `void`.
 * @throws No exceptions are propagated. sessionStorage write failures (for
 * example quota exceeded or private mode restrictions) are caught and ignored.
 */
export const writeCache = (key: string, objects: any[]) => {
  try {
    const payload: CacheEntry = { ts: Date.now(), objects };
    sessionStorage.setItem(key, JSON.stringify(payload));
  } catch {
    // ignore quota/private-mode errors
  }
};

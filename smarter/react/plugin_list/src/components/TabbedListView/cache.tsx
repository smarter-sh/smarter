/**
 * Tabbed list cache utilities.
 *
 * Stores plugin objects in localStorage using a key scoped by API URL and slug,
 * with a one-week TTL and automatic cleanup of expired entries.
 */
import type { Plugin } from "@/lib/Types";
import { projectName } from "@/const";

const CACHE_PREFIX = `${projectName}_objects_v1`;
const CACHE_TTL_MS = 7 * 24 * 60 * 60 * 1000; // 1 week

type CacheEntry = {
  ts: number;
  objects: Plugin[];
};

/**
 * Builds a stable localStorage key for a specific API endpoint and tab slug.
 *
 * @param apiUrl Base API URL used to scope cache entries by backend.
 * @param slug Tab or list identifier to isolate cached objects per view.
 * @returns A deterministic localStorage key in the format
 * `${CACHE_PREFIX}:${apiUrl}:${slug}`.
 * @throws This function does not throw under normal operation.
 */
export const makeCacheKey = (apiUrl: string, slug: string) => `${CACHE_PREFIX}:${apiUrl}:${slug}`;

/**
 * Reads and validates cached plugin objects.
 *
 * Returns null for missing, invalid, or expired entries and removes expired
 * data to keep storage clean.
 *
 * @param key Fully qualified localStorage cache key.
 * @returns The cached plugin array when present and valid; otherwise `null`.
 * @throws No exceptions are propagated. JSON parse errors, localStorage access
 * failures, and other runtime errors are caught and treated as a cache miss.
 */
export const readCache = (key: string): Plugin[] | null => {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return null;

    const parsed = JSON.parse(raw) as CacheEntry;
    if (!parsed || typeof parsed.ts !== "number" || !Array.isArray(parsed.objects)) return null;

    if (Date.now() - parsed.ts > CACHE_TTL_MS) {
      localStorage.removeItem(key);
      return null;
    }
    console.debug("cache hit for", key);
    return parsed.objects;
  } catch {
    return null;
  }
};

/**
 * Persists plugin objects to localStorage with a write timestamp.
 *
 * @param key Fully qualified localStorage cache key.
 * @param objects Plugin objects to cache for subsequent reads.
 * @returns `void`.
 * @throws No exceptions are propagated. localStorage write failures (for
 * example quota exceeded or private mode restrictions) are caught and ignored.
 */
export const writeCache = (key: string, objects: Plugin[]) => {
  try {
    const payload: CacheEntry = { ts: Date.now(), objects };
    localStorage.setItem(key, JSON.stringify(payload));
  } catch {
    // ignore quota/private-mode errors
  }
};

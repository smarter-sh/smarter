
import type { Plugin } from "@/lib/Types";

const CACHE_PREFIX = "prompt_list_chatbots_v1";
const CACHE_TTL_MS = 7 * 24 * 60 * 60 * 1000; // 1 week

type CacheEntry = {
  ts: number;
  objects: Plugin[];
};

export const makeCacheKey = (apiUrl: string, slug: string) => `${CACHE_PREFIX}:${apiUrl}:${slug}`;
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
    console.debug("cache hit   for", key);
    return parsed.objects;
  } catch {
    return null;
  }
};

export const writeCache = (key: string, objects: Plugin[]) => {
  try {
    const payload: CacheEntry = { ts: Date.now(), objects };
    localStorage.setItem(key, JSON.stringify(payload));
  } catch {
    // ignore quota/private-mode errors
  }
};

/**
 * useDashboardApi
 *
 * POSTs to a dashboard API endpoint, and returns its JSON response, or the
 * error message of a failed request. An empty url skips the request.
 *
 * By default it requests once, on mount. Two options change that:
 *
 * - ``maxAgeMs`` keeps the response in localStorage, and a later page load
 *   that finds one younger than this shows it at once, without a request.
 *   The dashboard is a full page load on every visit, so this is what lets a
 *   widget survive one. Use it only for data that isn't sensitive or specific
 *   to the user: localStorage outlives the session.
 * - ``refreshMs`` requests again once the response is this old, while the
 *   page is visible. A hidden tab doesn't poll; it refreshes stale data when
 *   it becomes visible again.
 *
 * ``refresh(body)`` requests again now, for a refresh button, with an optional
 * request body, such as ``{ refresh: true }`` for an endpoint that caches its
 * own results. ``refreshing`` is true until that request settles.
 *
 * The url is read once: a widget's url doesn't change.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { fetchDjangoUrl, gettext, interpolate } from "@smarter/common";
import type { SessionContext } from "@smarter/common";

import { loggerPrefix } from "@/const";

interface DashboardApiState<T> {
  data: T | null;
  error: string | null;
}

interface DashboardApiResult<T> extends DashboardApiState<T> {
  /** Requests again now, with this request body, or an empty one. */
  refresh: (body?: object) => void;
  /** Whether a request that refresh() started hasn't settled yet. */
  refreshing: boolean;
}

interface DashboardApiOptions {
  /** Reuse a response kept in localStorage while it's younger than this. */
  maxAgeMs?: number;
  /** Request again once the response is this old, while the page is visible. */
  refreshMs?: number;
}

/** A response kept in localStorage, and when it was received. */
interface CachedResponse<T> {
  savedAt: number;
  data: T;
}

/** How often a widget that polls checks whether its response is stale. Checking makes no request. */
const STALE_CHECK_MS = 30 * 1000;

function storageKey(url: string): string {
  return `smarter_dashboard_api:${url}`;
}

/** The response kept for this url, or null if there's none, or storage can't be read. */
function readCache<T>(url: string): CachedResponse<T> | null {
  try {
    const value = window.localStorage.getItem(storageKey(url));
    const cached = value ? (JSON.parse(value) as CachedResponse<T>) : null;
    return cached && typeof cached.savedAt === "number" ? cached : null;
  } catch {
    return null;
  }
}

function writeCache<T>(url: string, data: T): void {
  try {
    window.localStorage.setItem(storageKey(url), JSON.stringify({ savedAt: Date.now(), data }));
  } catch {
    // storage is full or blocked: the widget still works, it just requests on every page load.
  }
}

/** The response kept for this url, if it's younger than maxAgeMs. */
function freshCache<T>(url: string, maxAgeMs: number | undefined): CachedResponse<T> | null {
  if (!url || !maxAgeMs) return null;
  const cached = readCache<T>(url);
  return cached && Date.now() - cached.savedAt < maxAgeMs ? cached : null;
}

export default function useDashboardApi<T>(
  sessionContext: SessionContext,
  url: string,
  { maxAgeMs, refreshMs }: DashboardApiOptions = {},
): DashboardApiResult<T> {
  const [initial] = useState(() => freshCache<T>(url, maxAgeMs));
  const [state, setState] = useState<DashboardApiState<T>>({ data: initial?.data ?? null, error: null });
  // when the current response was received. A fresh cached one counts from when it was first received.
  const receivedAt = useRef<number | null>(initial?.savedAt ?? null);
  const [refreshing, setRefreshing] = useState(false);
  // the effect's load(), for refresh(). Null before the effect runs, and after the hook unmounts.
  const loadRef = useRef<((body?: object) => Promise<void>) | null>(null);

  useEffect(() => {
    if (!url) return;
    let cancelled = false;
    let loading = false;

    function load(body: object = {}): Promise<void> {
      loading = true;
      return fetchDjangoUrl(sessionContext, url, JSON.stringify(body))
        .then(async (response) => {
          if (!response.ok)
            throw new Error(interpolate(gettext("Request failed: %(status)s"), { status: response.status }));
          return (await response.json()) as T;
        })
        .then((data) => {
          receivedAt.current = Date.now();
          if (maxAgeMs) writeCache(url, data);
          if (!cancelled) setState({ data, error: null });
        })
        .catch((error: Error) => {
          console.error(loggerPrefix, "Error fetching", url, error);
          // try again at the next check, rather than after a whole refreshMs.
          receivedAt.current = null;
          if (!cancelled) setState({ data: null, error: error.message });
        })
        .finally(() => {
          loading = false;
        });
    }

    function refreshIfStale() {
      if (loading || document.visibilityState === "hidden") return;
      if (receivedAt.current === null || Date.now() - receivedAt.current >= (refreshMs as number)) load();
    }

    loadRef.current = load;
    if (receivedAt.current === null) load();
    if (!refreshMs) {
      return () => {
        cancelled = true;
        loadRef.current = null;
      };
    }
    const timer = window.setInterval(refreshIfStale, Math.min(refreshMs, STALE_CHECK_MS));
    document.addEventListener("visibilitychange", refreshIfStale);
    return () => {
      cancelled = true;
      loadRef.current = null;
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", refreshIfStale);
    };
  }, [sessionContext, url, maxAgeMs, refreshMs]);

  const refresh = useCallback((body?: object) => {
    const load = loadRef.current;
    if (!load) return;
    setRefreshing(true);
    load(body).finally(() => setRefreshing(false));
  }, []);

  return { ...state, refresh, refreshing };
}

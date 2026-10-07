/**
 * useDashboardApi
 *
 * POSTs to a dashboard API endpoint once, and returns its JSON response, or
 * the error message of a failed request. An empty url skips the request.
 */
import { useEffect, useState } from "react";
import { fetchDjangoUrl } from "@smarter/common";
import type { SessionContext } from "@smarter/common";

import { loggerPrefix } from "@/const";

interface DashboardApiState<T> {
  data: T | null;
  error: string | null;
}

export default function useDashboardApi<T>(sessionContext: SessionContext, url: string): DashboardApiState<T> {
  const [state, setState] = useState<DashboardApiState<T>>({ data: null, error: null });

  useEffect(() => {
    if (!url) return;
    let cancelled = false;
    fetchDjangoUrl(sessionContext, url, JSON.stringify({}))
      .then(async (response) => {
        if (!response.ok) throw new Error(`Request failed: ${response.status}`);
        return (await response.json()) as T;
      })
      .then((data) => {
        if (!cancelled) setState({ data, error: null });
      })
      .catch((error: Error) => {
        console.error(loggerPrefix, "Error fetching", url, error);
        if (!cancelled) setState({ data: null, error: error.message });
      });
    return () => {
      cancelled = true;
    };
  }, [sessionContext, url]);

  return state;
}

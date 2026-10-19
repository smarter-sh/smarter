/** The data of a Console tab that it fetches when it is first opened: the manifest, the architecture, or the deployment page. */
import { useEffect, useState } from "react";

export type TabData<T> = { data: T | null; error: string | null };

/**
 * Fetch a tab's data once, when the tab mounts.
 *
 * @param load - Fetches the data. It is called once.
 * @returns The data, or null while it loads, and the error that it raised, if any.
 */
export function useTabData<T>(load: () => Promise<T>): TabData<T> {
  const [state, setState] = useState<TabData<T>>({ data: null, error: null });
  useEffect(() => {
    let cancelled = false;
    load().then(
      (data) => {
        if (!cancelled) setState({ data, error: null });
      },
      (error: unknown) => {
        if (!cancelled) setState({ data: null, error: error instanceof Error ? error.message : String(error) });
      },
    );
    return () => {
      cancelled = true;
    };
    // the tab's data is fetched once: a tab that is opened again keeps what it has.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return state;
}

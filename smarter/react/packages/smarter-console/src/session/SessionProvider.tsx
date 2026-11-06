/**
 * The console's session: who is using it, and how the platform is set up, from GET /api/web/session/.
 *
 * The provider loads it once when the console starts. Components read it with useConsoleSession(), and call
 * refresh() after anything that changes it: signing in, signing out, or changing profile.
 */
import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";

import type { ConsoleSession } from "@/contract.gen";
import { getJson } from "@/lib/api";
import { loggerPrefix, SESSION_API_URL } from "@/lib/const";
import { SessionContext, type SessionState } from "@/session/context";

export function SessionProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<ConsoleSession | null>(null);
  const [error, setError] = useState<Error | null>(null);

  /** Load the session, then keep it, or the error. */
  const load = useCallback(() => {
    return getJson<ConsoleSession>(SESSION_API_URL).then(
      (response) => {
        setSession(response);
        setError(null);
      },
      (e: unknown) => {
        console.error(`${loggerPrefix} SessionProvider could not load the session:`, e);
        setError(e instanceof Error ? e : new Error(String(e)));
      },
    );
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const refresh = useCallback(async () => {
    await load();
  }, [load]);

  // the page's language follows the session's, as Django's base template did.
  useEffect(() => {
    if (!session) return;
    document.documentElement.lang = session.language.current;
    document.documentElement.dir = session.language.bidi ? "rtl" : "ltr";
  }, [session]);

  const replace = useCallback((next: ConsoleSession) => {
    setSession(next);
    setError(null);
  }, []);

  const value = useMemo<SessionState>(() => ({ session, error, refresh, replace }), [session, error, refresh, replace]);
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

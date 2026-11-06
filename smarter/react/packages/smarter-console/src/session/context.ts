/** The console session's React context, and the hook that reads it. See SessionProvider. */
import { createContext, useContext } from "react";

import type { ConsoleSession } from "@/contract.gen";

export interface SessionState {
  /** The session, or null until it has loaded. */
  session: ConsoleSession | null;
  /** Why the session couldn't be loaded, or null. */
  error: Error | null;
  /** Load the session again, after signing in or out, or changing profile. */
  refresh: () => Promise<void>;
}

export const SessionContext = createContext<SessionState | null>(null);

/** The console's session state. Only components inside a SessionProvider may call it. */
export function useConsoleSession(): SessionState {
  const state = useContext(SessionContext);
  if (!state) {
    throw new Error("useConsoleSession() must be called inside a SessionProvider.");
  }
  return state;
}

/**
 * The guard of the console's signed-in routes: a visitor who isn't signed in is sent to the sign-in page,
 * which returns them here afterwards.
 */
import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router";

import { LOGIN_PATH, NEXT_PARAMETER } from "@/lib/const";
import { useConsoleSession } from "@/session/context";

export function RequireAuth({ children }: { children: ReactNode }) {
  const { session } = useConsoleSession();
  const location = useLocation();
  if (session && !session.isAuthenticated) {
    const next = `${location.pathname}${location.search}`;
    const query = new URLSearchParams({ [NEXT_PARAMETER]: next });
    return <Navigate to={`${LOGIN_PATH}?${query.toString()}`} replace />;
  }
  return <>{children}</>;
}

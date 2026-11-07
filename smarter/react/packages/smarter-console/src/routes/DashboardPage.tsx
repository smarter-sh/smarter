/**
 * The console's dashboard, /dashboard: @smarter/dashboard's widgets, with their context from the session. Its context
 * is made once per session, so that a re-render doesn't give the widgets a new one, which would make them load again.
 */
import { Dashboard } from "@smarter/dashboard";
import { useMemo } from "react";

import { dashboardContext } from "@/lib/dashboard";
import { useConsoleSession } from "@/session/context";

export function DashboardPage() {
  const { session } = useConsoleSession();
  const appContext = useMemo(() => (session ? dashboardContext(session) : null), [session]);
  if (!appContext) return null;
  return <Dashboard appContext={appContext} />;
}

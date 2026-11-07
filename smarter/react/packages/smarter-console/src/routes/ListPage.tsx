/**
 * A resource list of lib/lists: the package's list component, with a session context from the console's session
 * whose ApiUrl is the list's api, and the onboarding hints' state. They are made once per session, so that a
 * re-render doesn't reload the list. A list that the session may not see is not found, as the backend's page was.
 */
import { useMemo } from "react";

import { djangoSessionContext } from "@/lib/djangoSession";
import type { ListComponent, ListPage as ListPageConfig } from "@/lib/lists";
import { onboardingContext } from "@/lib/welcome";
import { NotFoundPage } from "@/routes/NotFoundPage";
import { useConsoleSession } from "@/session/context";

interface ListPageProps {
  page: ListPageConfig;
  List: ListComponent;
}

export function ListPage({ page, List }: ListPageProps) {
  const { session } = useConsoleSession();
  const sessionContext = useMemo(
    () => (session ? djangoSessionContext(session, page.apiUrl) : null),
    [session, page.apiUrl],
  );
  const onboarding = useMemo(() => (session ? onboardingContext(session) : null), [session]);
  if (!session || !sessionContext) return null;
  if (page.visible && !page.visible(session)) return <NotFoundPage />;
  return <List sessionContext={sessionContext} onboarding={onboarding} />;
}

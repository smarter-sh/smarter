/**
 * A resource list of lib/lists: the package's list component, with a session context from the console's session
 * whose ApiUrl is the list's api. The context is made once per session, so that a re-render doesn't reload the list.
 */
import { useMemo } from "react";

import { djangoSessionContext } from "@/lib/djangoSession";
import type { ListComponent, ListPage as ListPageConfig } from "@/lib/lists";
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
  if (!sessionContext) return null;
  return <List sessionContext={sessionContext} />;
}

/**
 * The resource lists that have moved into the console. Each is a package's list component (@smarter/<kind>-list)
 * at the path that Django served it at, without the trailing slash, with its list api in the console's web api. The
 * router gives each a route, whose component loads in a chunk of its own; the sidebar opens it in place.
 */
import type { SessionContext } from "@smarter/common";
import type { ComponentType } from "react";

/** A list component: what each package's src/index.ts exports. */
export type ListComponent = ComponentType<{ sessionContext: SessionContext }>;

export interface ListPage {
  /** The console's route, e.g. /guardrail: Django's /guardrail/. */
  path: string;
  /** The list api, /api/web/<app>/listview/, whose owned/, shared/ and all/ the list calls. */
  apiUrl: string;
  /** Loads the package's list component. */
  load: () => Promise<ListComponent>;
}

export const LIST_PAGES: ListPage[] = [
  {
    path: "/guardrail",
    apiUrl: "/api/web/guardrail/listview/",
    load: async () => (await import("@smarter/guardrail-list")).GuardrailList,
  },
];

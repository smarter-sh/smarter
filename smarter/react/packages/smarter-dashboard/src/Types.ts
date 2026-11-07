/**
 * The dashboard's context: the cookies and headers of its requests, and the urls of its widgets' endpoints in the
 * console's dashboard api, /api/web/dashboard/. See smarter.apps.dashboard.views.views.api.urls.
 */
import type { SessionContext } from "@smarter/common";

export interface AppContextInterface {
  sessionContext: SessionContext;
  myResourcesApiUrl: string;
  serviceHealthApiUrl: string;
  chargesApiUrl: string;
  budgetsApiUrl: string;
  activityApiUrl: string;
  gettingStartedApiUrl: string;
  quickActionsApiUrl: string;
  globalSearchApiUrl: string;
}

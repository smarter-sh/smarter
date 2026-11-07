/**
 * The dashboard's context, from the console's session: its widgets' endpoints in the console's dashboard api,
 * /api/web/dashboard/. See smarter.apps.dashboard.views.views.api.urls.
 */
import type { DashboardContext } from "@smarter/dashboard";

import type { ConsoleSession } from "@/contract.gen";
import { djangoSessionContext } from "@/lib/djangoSession";

/** The console's dashboard api. */
export const DASHBOARD_API = "/api/web/dashboard";

export const dashboardUrls = {
  myResources: `${DASHBOARD_API}/my-resources/`,
  serviceHealth: `${DASHBOARD_API}/service-health/`,
  charges: `${DASHBOARD_API}/charges/`,
  budgets: `${DASHBOARD_API}/budgets/`,
  activity: `${DASHBOARD_API}/activity/`,
  gettingStarted: `${DASHBOARD_API}/getting-started/`,
  quickActions: `${DASHBOARD_API}/quick-actions/`,
  globalSearch: `${DASHBOARD_API}/search/`,
};

/**
 * The dashboard's context.
 *
 * @param session - The console's session.
 * @returns The context, with a new request id.
 */
export function dashboardContext(session: ConsoleSession): DashboardContext {
  return {
    // the dashboard sends the "custom" capability, as it did from its template.
    sessionContext: djangoSessionContext(session, dashboardUrls.myResources, ["custom"]),
    myResourcesApiUrl: dashboardUrls.myResources,
    serviceHealthApiUrl: dashboardUrls.serviceHealth,
    chargesApiUrl: dashboardUrls.charges,
    budgetsApiUrl: dashboardUrls.budgets,
    activityApiUrl: dashboardUrls.activity,
    gettingStartedApiUrl: dashboardUrls.gettingStarted,
    quickActionsApiUrl: dashboardUrls.quickActions,
    globalSearchApiUrl: dashboardUrls.globalSearch,
  };
}

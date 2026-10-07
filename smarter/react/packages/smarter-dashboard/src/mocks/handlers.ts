/**
 * MSW request handlers for the Django dashboard api. Stories and tests use them to answer its
 * requests. See storybook/preview.ts and test/server.ts in the workspace.
 */
import { http, HttpResponse } from "msw";

import {
  activity,
  appContext,
  budgetSeries,
  budgets,
  gettingStarted,
  myResources,
  quickActions,
  serviceHealth,
  tokenUsage,
} from "./fixtures";

export const myResourcesHandler = http.post(appContext.myResourcesApiUrl, () => HttpResponse.json(myResources));
export const serviceHealthHandler = http.post(appContext.serviceHealthApiUrl, () => HttpResponse.json(serviceHealth));
export const quickActionsHandler = http.post(appContext.quickActionsApiUrl, () => HttpResponse.json(quickActions));
export const gettingStartedHandler = http.post(appContext.gettingStartedApiUrl, () =>
  HttpResponse.json(gettingStarted),
);
export const activityHandler = http.post(appContext.activityApiUrl, () => HttpResponse.json(activity));
export const chargesHandler = http.post(`${appContext.chargesApiUrl}:periodicity/`, () =>
  HttpResponse.json(tokenUsage),
);
export const budgetsHandlers = [
  http.post(appContext.budgetsApiUrl, () => HttpResponse.json(budgets)),
  http.post(`${appContext.budgetsApiUrl}:locator/series/`, () => HttpResponse.json(budgetSeries)),
];

/** Every dashboard api. */
export const dashboardHandlers = [
  myResourcesHandler,
  serviceHealthHandler,
  quickActionsHandler,
  gettingStartedHandler,
  activityHandler,
  chargesHandler,
  ...budgetsHandlers,
];

/** Every dashboard api fails. */
export const dashboardErrorHandlers = [
  http.post("/dashboard/api/*", () => HttpResponse.json({ error: "Service unavailable" }, { status: 503 })),
];

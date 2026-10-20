/**
 * MSW request handlers for the Django welcome api. Stories and tests use them to answer its
 * requests. See storybook/preview.ts and test/server.ts in the workspace.
 */
import { http, HttpResponse } from "msw";

import { appContext, welcome } from "./fixtures";

export const welcomeHandler = http.post(appContext.apiUrl, () => HttpResponse.json(welcome));
export const dismissHandler = http.post(appContext.dismissApiUrl, () =>
  HttpResponse.json({ ...welcome, welcomed: true }),
);

/** Both welcome apis. */
export const welcomeHandlers = [welcomeHandler, dismissHandler];

/** A user who can't read a Get Weather LLMClient. */
export const noWeatherHandlers = [
  http.post(appContext.apiUrl, () => HttpResponse.json({ ...welcome, urls: { ...welcome.urls, weather: null } })),
  dismissHandler,
];

/** Both welcome apis fail. */
export const welcomeErrorHandlers = [
  http.post("/dashboard/api/welcome/*", () => HttpResponse.json({ error: "Service unavailable" }, { status: 503 })),
  http.post(appContext.apiUrl, () => HttpResponse.json({ error: "Service unavailable" }, { status: 503 })),
];

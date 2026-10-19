/**
 * MSW request handlers for the workbench's api key actions. Stories and tests use them to answer the
 * app's requests. See storybook/preview.ts and test/server.ts in the workspace.
 */
import { http, HttpResponse } from "msw";

import type { ApiKeyActionResponse, ErrorResponse } from "@/lib/types";

import { ATTACH_URL, CREATE_URL, DETACH_URL, attachedResponse, createdResponse, detachedResponse } from "./fixtures";

/** Every action succeeds. */
export function actionHandlers(
  created: ApiKeyActionResponse = createdResponse,
  attached: ApiKeyActionResponse = attachedResponse,
  detached: ApiKeyActionResponse = detachedResponse,
) {
  return [
    http.post(CREATE_URL, () => HttpResponse.json(created)),
    http.post(ATTACH_URL, () => HttpResponse.json(attached)),
    http.post(DETACH_URL, () => HttpResponse.json(detached)),
  ];
}

/** Every action fails, with the api's error. */
export function errorHandlers(error: ErrorResponse, status = 400) {
  return [CREATE_URL, ATTACH_URL, DETACH_URL].map((url) => http.post(url, () => HttpResponse.json(error, { status })));
}

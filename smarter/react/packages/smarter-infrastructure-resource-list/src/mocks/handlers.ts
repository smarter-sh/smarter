/**
 * MSW request handlers for the Django api that this package calls. Stories and tests use them
 * to answer its requests. See storybook/preview.ts and test/server.ts in the workspace.
 */
import { http, HttpResponse } from "msw";

import type { InfrastructureResourceListResponse } from "@/lib/Types";

import { API_URL, listResponse } from "./fixtures";

/** The list api. */
export function listHandlers(response: InfrastructureResourceListResponse = listResponse) {
  return [http.post(API_URL, () => HttpResponse.json(response))];
}

/** The list api fails. */
export const listErrorHandlers = [http.post(API_URL, () => new HttpResponse(null, { status: 500 }))];

/** The list api refuses a user who is not a superuser. */
export const listForbiddenHandlers = [
  http.post(API_URL, () =>
    HttpResponse.json({ error: "Only superusers may see the platform's infrastructure resources." }, { status: 403 }),
  ),
];

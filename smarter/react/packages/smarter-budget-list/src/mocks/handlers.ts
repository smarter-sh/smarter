/**
 * MSW request handlers for the Django api that this package calls. Stories and tests use them
 * to answer its requests. See storybook/preview.ts and test/server.ts in the workspace.
 */
import { http, HttpResponse } from "msw";

import type { BudgetListResponse } from "@/lib/Types";

import { API_URL, SERIES_URL, listResponse, series } from "./fixtures";

/** The list api, and each resource's budget versus actual series. */
export function listHandlers(response: BudgetListResponse = listResponse) {
  return [
    http.post(API_URL, () => HttpResponse.json(response)),
    http.post(SERIES_URL, () =>
      HttpResponse.json(response.objects.map((budget) => ({ status: { budget: budget.name }, series }))),
    ),
  ];
}

/** The delete api, which succeeds. */
export const deleteHandlers = [
  http.post("/budget/react-integration/api/delete/:id/", ({ params }) =>
    HttpResponse.json({ message: `Budget ${params.id} deleted.` }),
  ),
];

/** The list api fails. */
export const listErrorHandlers = [http.post(API_URL, () => new HttpResponse(null, { status: 500 }))];

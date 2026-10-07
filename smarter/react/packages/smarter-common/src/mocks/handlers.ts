/** MSW request handlers for the example list api. See mocks/example.tsx. */
import { http, HttpResponse } from "msw";

import { API_URL, type Example, ownedExamples, sharedExamples } from "./example";

export function listHandlers(owned: Example[] = ownedExamples, shared: Example[] = sharedExamples) {
  return [
    http.post(`${API_URL}owned/`, () => HttpResponse.json({ objects: owned })),
    http.post(`${API_URL}shared/`, () => HttpResponse.json({ objects: shared })),
  ];
}

export const listErrorHandlers = [
  http.post(`${API_URL}:tab/`, () => HttpResponse.json({ error: "Database unavailable" }, { status: 500 })),
];

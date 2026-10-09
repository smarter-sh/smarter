/** MSW request handlers for the example list api. See mocks/example.tsx. */
import { http, HttpResponse } from "msw";

import { API_URL, type Example, ownedExamples, sharedExamples } from "./example";

/**
 * A page of the examples that match the request's search, as the Django list api returns it
 * (see smarter.lib.django.pagination): ?page, ?page_size and ?search are all optional.
 */
export function examplePage(examples: Example[], requestUrl: string, defaultPageSize = 25) {
  const params = new URL(requestUrl).searchParams;
  const search = (params.get("search") ?? "").trim().toLowerCase();
  const pageSize = Number(params.get("page_size")) || defaultPageSize;
  const matches = examples.filter((example) => example.name.toLowerCase().includes(search));
  const numPages = Math.max(1, Math.ceil(matches.length / pageSize));
  const page = Math.min(Math.max(1, Number(params.get("page")) || 1), numPages);
  return {
    objects: matches.slice((page - 1) * pageSize, page * pageSize),
    pagination: { page, pageSize, numPages, count: matches.length, search },
  };
}

export function listHandlers(owned: Example[] = ownedExamples, shared: Example[] = sharedExamples, pageSize = 25) {
  return [
    http.post(`${API_URL}owned/`, ({ request }) => HttpResponse.json(examplePage(owned, request.url, pageSize))),
    http.post(`${API_URL}shared/`, ({ request }) => HttpResponse.json(examplePage(shared, request.url, pageSize))),
  ];
}

/** Enough examples, named example_1 to example_<count>, for several pages. */
export function manyExamples(count: number): Example[] {
  return Array.from({ length: count }, (_, index) => ({ id: index + 1, name: `example_${index + 1}` }));
}

export const listErrorHandlers = [
  http.post(`${API_URL}:tab/`, () => HttpResponse.json({ error: "Database unavailable" }, { status: 500 })),
];

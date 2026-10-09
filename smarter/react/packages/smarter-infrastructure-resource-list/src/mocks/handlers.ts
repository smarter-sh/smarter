/**
 * MSW request handlers for the Django api that this package calls. Stories and tests use them
 * to answer its requests. See storybook/preview.ts and test/server.ts in the workspace.
 */
import { http, HttpResponse } from "msw";

import type { InfrastructureResource, InfrastructureResourceListResponse } from "@/lib/Types";

import { API_URL, resources, summarize } from "./fixtures";

type ListRequest = {
  status?: string;
  billableOnly?: boolean;
  provider?: string;
  resourceType?: string;
  text?: string;
  page?: number;
  pageSize?: number;
};

/** Filter and paginate resources, as smarter.apps.infrastructure.views.listview does. */
export function listResponseFor(
  objects: InfrastructureResource[],
  request: ListRequest,
): InfrastructureResourceListResponse {
  const text = (request.text ?? "").toLowerCase();
  const matches = objects.filter(
    (resource) =>
      (!request.status || request.status === "all" || resource.status === request.status) &&
      (!request.billableOnly || resource.billable) &&
      (!request.provider || resource.provider === request.provider) &&
      (!request.resourceType || resource.resourceType === request.resourceType) &&
      (!text ||
        [resource.resourceName, resource.resourceType, resource.resourceId, resource.service].some((value) =>
          value.toLowerCase().includes(text),
        )),
  );
  const pageSize = request.pageSize ?? 50;
  const numPages = Math.max(1, Math.ceil(matches.length / pageSize));
  const page = Math.min(Math.max(1, request.page ?? 1), numPages);
  return {
    summary: summarize(objects),
    objects: matches.slice((page - 1) * pageSize, page * pageSize),
    pagination: { page, pageSize, numPages, count: matches.length },
    choices: {
      providers: Array.from(new Set(objects.map((resource) => resource.provider))).sort(),
      resourceTypes: Array.from(new Set(objects.map((resource) => resource.resourceType))).sort(),
    },
  };
}

/** The list api, over some resources. */
export function listHandlers(objects: InfrastructureResource[] = resources) {
  return [
    http.post(API_URL, async ({ request }) =>
      HttpResponse.json(listResponseFor(objects, (await request.json()) as ListRequest)),
    ),
  ];
}

/** The list api fails. */
export const listErrorHandlers = [http.post(API_URL, () => new HttpResponse(null, { status: 500 }))];

/** The list api refuses a user who is not a superuser. */
export const listForbiddenHandlers = [
  http.post(API_URL, () =>
    HttpResponse.json({ error: "Only superusers may see the platform's infrastructure resources." }, { status: 403 }),
  ),
];

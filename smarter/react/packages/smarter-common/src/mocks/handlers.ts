/** MSW request handlers for the example list api. See mocks/example.tsx. */
import { http, HttpResponse } from "msw";

import type { ResourceDetailData } from "../components/ResourceDetail/api";
import { API_URL, type Example, type Other, otherObjects, ownedExamples, sharedExamples } from "./example";
import { guardrailDependents, guardrailTree } from "./resourceTree";

/** The columns that the example list api can sort by. */
export const EXAMPLE_SORT_FIELDS = ["name"];

/**
 * A page of the examples that match the request's search, in its order, as the Django list api
 * returns it (see smarter.lib.django.pagination): ?page, ?page_size, ?search and ?ordering are all
 * optional. ?ordering=name sorts the examples by name, and ?ordering=-name in descending order.
 */
export function examplePage(examples: Example[], requestUrl: string, defaultPageSize = 25) {
  const params = new URL(requestUrl).searchParams;
  const search = (params.get("search") ?? "").trim().toLowerCase();
  const pageSize = Number(params.get("page_size")) || defaultPageSize;
  const requested = params.get("ordering") ?? "";
  const ordering = EXAMPLE_SORT_FIELDS.includes(requested.replace(/^-/, "")) ? requested : "";
  // the list api's one named filter, "even": the examples with an even id. It ignores any other.
  const filter = params.get("filter") === "even" ? "even" : "";
  // tags, and an annotation selector of "key=value" requirements. A requirement with a space is
  // invalid, and reported, not applied, as the list api does.
  const tags = params.getAll("tag");
  const requestedAnnotations = params.getAll("annotation");
  const invalid = requestedAnnotations.find((requirement) => requirement.includes(" "));
  const annotations = invalid ? [] : requestedAnnotations;
  const annotationError = invalid ? `Annotation key '${invalid}' is invalid.` : "";
  const annotated = (example: Example, requirement: string) => {
    const [key, value] = requirement.split("=", 2);
    return value === undefined ? key in (example.annotations ?? {}) : example.annotations?.[key] === value;
  };
  const matches = examples.filter(
    (example) =>
      example.name.toLowerCase().includes(search) &&
      (!filter || example.id % 2 === 0) &&
      tags.every((tag) => example.tags?.includes(tag)) &&
      annotations.every((requirement) => annotated(example, requirement)),
  );
  if (ordering) {
    const direction = ordering.startsWith("-") ? -1 : 1;
    matches.sort((a, b) => direction * (a.name < b.name ? -1 : a.name > b.name ? 1 : 0));
  }
  const numPages = Math.max(1, Math.ceil(matches.length / pageSize));
  const page = Math.min(Math.max(1, Number(params.get("page")) || 1), numPages);
  return {
    objects: matches.slice((page - 1) * pageSize, page * pageSize),
    pagination: {
      page,
      pageSize,
      numPages,
      count: matches.length,
      search,
      ordering,
      sortFields: EXAMPLE_SORT_FIELDS,
      filter,
      filters: ["even"],
      tags,
      annotations,
      annotationError,
    },
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
  return Array.from({ length: count }, (_, index) => ({
    id: index + 1,
    name: `example_${index + 1}`,
    detailUrl: `/dashboard/api/resource/Example/example-r${index + 1}/`,
  }));
}

/** An example's manifest, as the detail returns it. */
export function exampleManifest(name: string): string {
  return [
    "apiVersion: smarter.sh/v1",
    "kind: Guardrail",
    "metadata:",
    `  name: ${name}`,
    "  description: 'Redact personal data # not a comment'",
    "  version: 1.0.0",
    "  tags:",
    "  - red",
    "spec:",
    "  # what the guardrail does",
    "  enabled: true",
    "  threshold: 0.85",
    "  prompt: |",
    "    key: inside a block scalar",
    "    is text",
    "  replacement: null",
    "",
  ].join("\n");
}

/** The detail of an example, as smarter.apps.dashboard.resource_detail returns it. */
export function exampleDetail(id: number, name: string, dependents = guardrailDependents): ResourceDetailData {
  return {
    kind: "Guardrail",
    name,
    recordLocator: `example-r${id}`,
    url: `/guardrail/guardrails/r${id}/`,
    manifest: exampleManifest(name),
    manifestError: "",
    tree: { ...guardrailTree, name, recordLocator: `example-r${id}` },
    dependents,
  };
}

/** The detail api of the examples: see exampleDetailUrl. */
export function detailHandler(dependents = guardrailDependents) {
  return http.post("/dashboard/api/resource/Example/:locator/", ({ params }) => {
    const id = Number(String(params.locator).replace("example-r", ""));
    const name = ownedExamples.find((example) => example.id === id)?.name ?? `example_${id}`;
    return HttpResponse.json(exampleDetail(id, name, dependents));
  });
}

export const listErrorHandlers = [
  http.post(`${API_URL}:tab/`, () => HttpResponse.json({ error: "Database unavailable" }, { status: 500 })),
];

/** The handler of the other tab's list api: see exampleContextWithOtherTab. */
export function otherHandler(others: Other[] = otherObjects) {
  return http.post(`${API_URL}others/`, () => HttpResponse.json({ objects: others }));
}

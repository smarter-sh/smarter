/**
 * MSW request handlers for the Django api that this package calls. Stories and tests use them
 * to answer its requests. See storybook/preview.ts and test/server.ts in the workspace.
 */
import { http, HttpResponse } from "msw";

import type { Extension, LLMTool } from "@/lib/Types";

import {
  ACTIONS_URL as BASE,
  API_URL,
  extensionObjects,
  extensionPage,
  makeObject,
  ownedObjects,
  sharedObjects,
} from "./fixtures";

/** The list api: the owned and shared objects, and the extensions of the read-only Extensions tab. */
export function listHandlers(
  owned: LLMTool[] = ownedObjects,
  shared: LLMTool[] = sharedObjects,
  extensions: Extension[] = extensionObjects,
) {
  return [
    http.post(`${API_URL}owned/`, () => HttpResponse.json({ objects: owned })),
    http.post(`${API_URL}shared/`, () => HttpResponse.json({ objects: shared })),
    http.post(`${API_URL}extensions/`, () => HttpResponse.json(extensionPage(extensions))),
  ];
}

/** The clone, rename and delete apis, which succeed. */
export const actionHandlers = [
  http.post(`${BASE}clone/:id/:newName/`, ({ params }) =>
    HttpResponse.json(makeObject(99, { name: String(params.newName) })),
  ),
  http.post(`${BASE}rename/:id/:newName/`, ({ params }) =>
    HttpResponse.json(makeObject(1, { name: String(params.newName) })),
  ),
  http.post(`${BASE}delete/:id/`, ({ params }) => HttpResponse.json({ message: `${params.id} deleted.` })),
];

/** The list api fails. */
export const listErrorHandlers = [
  http.post(`${API_URL}:tab/`, () => HttpResponse.json({ error: "Database unavailable" }, { status: 500 })),
];

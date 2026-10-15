/**
 * MSW request handlers for the Extensions api. Stories and tests use them to answer the app's
 * requests. See storybook/preview.ts and test/server.ts in the workspace.
 */
import { http, HttpResponse } from "msw";

import type { ExtensionDetail, ExtensionListResponse, RegistryResponse } from "@/lib/types";

import { API_URL, accounts, action, detail, listResponse, makeDetail, makeSummary, registryResponse } from "./fixtures";

/** The list and registry apis. */
export function listHandlers(
  list: ExtensionListResponse = listResponse,
  registry: RegistryResponse = registryResponse,
) {
  return [
    http.post(`${API_URL}list/`, () => HttpResponse.json(list)),
    http.post(`${API_URL}registry/`, () => HttpResponse.json(registry)),
    http.post(`${API_URL}check-updates/`, () =>
      HttpResponse.json(action("Updates are available: Weather 0.2.0.", null)),
    ),
    http.post(`${API_URL}install/`, async ({ request }) => {
      const body = (await request.json()) as { slug: string };
      return HttpResponse.json(
        action(
          "Installed.",
          makeDetail({ ...makeSummary({ slug: body.slug, detailUrl: `/extensions/${body.slug}/` }) }),
        ),
      );
    }),
    http.post(`${API_URL}upload/`, () =>
      HttpResponse.json(
        action("Installed Acme CRM 1.0.0.", makeDetail({ slug: "acme-crm", detailUrl: "/extensions/acme-crm/" })),
      ),
    ),
    http.post(`${API_URL}extensions/:slug/enable/`, () =>
      HttpResponse.json(action("Enabled.", makeDetail({ enabled: true }))),
    ),
    http.post(`${API_URL}extensions/:slug/disable/`, () =>
      HttpResponse.json(action("Disabled.", makeDetail({ enabled: false }))),
    ),
  ];
}

/** The detail api of one extension, and its actions, which succeed. */
export function detailHandlers(extension: ExtensionDetail = detail) {
  return [
    http.post(`${API_URL}extensions/:slug/`, () => HttpResponse.json({ extension })),
    http.post(`${API_URL}extensions/:slug/enable/`, () =>
      HttpResponse.json(action(`Enabled ${extension.displayName}.`, { ...extension, enabled: true })),
    ),
    http.post(`${API_URL}extensions/:slug/disable/`, () =>
      HttpResponse.json(action(`Disabled ${extension.displayName}.`, { ...extension, enabled: false })),
    ),
    http.post(`${API_URL}extensions/:slug/update/`, () =>
      HttpResponse.json(
        action(`Updated ${extension.displayName} to 0.2.0.`, {
          ...extension,
          installedVersion: "0.2.0",
          updateAvailable: false,
        }),
      ),
    ),
    http.post(`${API_URL}extensions/:slug/rollback/`, () =>
      HttpResponse.json(action(`Rolled ${extension.displayName} back to 0.0.9.`, extension)),
    ),
    http.post(`${API_URL}extensions/:slug/configure/`, () =>
      HttpResponse.json(action(`Saved the settings of ${extension.displayName}.`, extension)),
    ),
    http.post(`${API_URL}extensions/:slug/availability/`, async ({ request }) => {
      const body = (await request.json()) as { allAccounts: boolean };
      return HttpResponse.json(
        action(body.allAccounts ? "Available to every account." : "Available to 1 account(s).", {
          ...extension,
          allAccounts: body.allAccounts,
        }),
      );
    }),
    http.post(`${API_URL}extensions/:slug/uninstall/`, () =>
      HttpResponse.json(action(`Uninstalled ${extension.displayName}.`, null)),
    ),
    http.post(`${API_URL}accounts/`, () => HttpResponse.json({ objects: accounts })),
  ];
}

/** Every request fails, as an api error. */
export const errorHandlers = [
  http.post(`${API_URL}*`, () => HttpResponse.json({ error: "Database unavailable" }, { status: 500 })),
];

/**
 * An MSW handler of the resource detail api, for the tests of a list package that open a row's detail: the
 * Manifest, Hierarchy and Dependencies tabs of @smarter/common's ResourceDetail, which TabbedListView opens when a
 * row is chosen. See smarter.apps.dashboard.resource_detail in the backend.
 *
 *     import { resourceDetailHandler } from "@test/resourceDetail";
 *     server.use(...listHandlers(), resourceDetailHandler());
 *
 * Each list's object has its detailUrl, /dashboard/api/resource/<kind>/<record locator>/, which the fixtures of
 * the list packages give as detailUrl(kind, id).
 */
import { http, HttpResponse } from "msw";

/** The url of a resource's detail, as a list api's serializer sends it, e.g. for a fixture's detailUrl. */
export function detailUrl(kind: string, id: number | string): string {
  return `/dashboard/api/resource/${kind}/${kind.toLowerCase()}-r${id}/`;
}

/** The detail that the handler returns: the resource uses one Secret, and one LLMClient uses it. */
export function resourceDetail(kind: string, recordLocator: string) {
  const name = `resource_${recordLocator}`;
  return {
    kind,
    name,
    recordLocator,
    url: `/console/${recordLocator}/`,
    manifest: `apiVersion: smarter.sh/v1\nkind: ${kind}\nmetadata:\n  name: ${name}\nspec: {}\n`,
    manifestError: "",
    tree: {
      kind,
      icon: "abstract-26",
      name,
      owner: "Ada Lovelace (ada)",
      recordLocator,
      url: `/console/${recordLocator}/`,
      readable: true,
      children: [
        {
          kind: "Secret",
          icon: "lock-2",
          name: "api_key",
          owner: "Ada Lovelace (ada)",
          recordLocator: "secret-rMQx",
          url: "/secret/secrets/rMQx/",
          readable: true,
          children: [],
        },
      ],
    },
    dependents: [
      {
        kind: "LLMClient",
        icon: "artificial-intelligence",
        name: "stackademy",
        owner: "Ada Lovelace (ada)",
        recordLocator: "llmclient-rMQx",
        url: "/workbench/llm-clients/rMQx/manifest/",
        readable: true,
        children: [],
      },
    ],
  };
}

/** Answers every resource's detail. */
export function resourceDetailHandler() {
  return http.post("/dashboard/api/resource/:kind/:recordLocator/", ({ params }) =>
    HttpResponse.json(resourceDetail(String(params.kind), String(params.recordLocator))),
  );
}

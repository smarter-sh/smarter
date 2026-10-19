import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { workbenchPage } from "@smarter/llmclient-deployment/mocks";

import { ApiError, fetchDeploymentPage, fetchManifest } from "@/lib/api";
import { DEPLOYMENT_URL, MANIFEST_URL, MANIFEST_YAML } from "@/mocks/fixtures";
import { tabHandlers } from "@/mocks/handlers";
import { server } from "@test/server";

describe("the workbench's own requests", () => {
  it("fetch the manifest, and the deployment page, with the user's session", async () => {
    let credentials: RequestCredentials | null = null;
    server.use(
      http.get(MANIFEST_URL, ({ request }) => {
        credentials = request.credentials;
        return HttpResponse.json({ manifest: MANIFEST_YAML });
      }),
      ...tabHandlers,
    );
    expect(await fetchManifest(MANIFEST_URL)).toBe(MANIFEST_YAML);
    expect(credentials).toBe("same-origin");
    expect(await fetchDeploymentPage(DEPLOYMENT_URL)).toEqual(workbenchPage);
  });

  it("throw an ApiError for a failed response", async () => {
    server.use(http.get(MANIFEST_URL, () => new HttpResponse(null, { status: 403, statusText: "Forbidden" })));
    const error = await fetchManifest(MANIFEST_URL).catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 403, message: "The request failed: 403 Forbidden" });
  });
});

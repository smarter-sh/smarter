/** The manifest pages: a resource's manifest in the manifest editor, at the path that Django served it at. */
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { createMemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { dashboardHandlers } from "@smarter/dashboard/mocks";
import { listHandlers } from "@smarter/secret-list/mocks";
import { cliHandlers } from "@smarter/manifest-editor/mocks";

import { server } from "@test/server";

import App from "@/App";
import { MANIFEST_PAGES, recordLocator, resourceUrl } from "@/lib/manifestPages";
import { userSession } from "@/mocks/fixtures";
import { sessionHandler, userSessionHandler } from "@/mocks/handlers";
import { routes } from "@/router";

// Monaco loads from a CDN at runtime, which jsdom can't: the editor package's stand-in is a textarea.
vi.mock("@monaco-editor/react", async () => await import("@smarter/manifest-editor/mocks/monaco"));

const SECRET_YAML = `apiVersion: smarter.sh/v1
kind: Secret
metadata:
  name: example_secret
  description: An example secret.
  version: 1.0.0
spec:
  config:
    value: not-a-real-secret
`;

function mountAt(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  render(<App router={router} />);
  return router;
}

/** The resource api answers with the secret's manifest. */
function resourceHandler(manifest: string | null = SECRET_YAML, manifestError = "") {
  return http.get(resourceUrl("secret-rMTAwx"), () =>
    HttpResponse.json({
      kind: "Secret",
      name: "example_secret",
      recordLocator: "secret-rMTAwx",
      manifest,
      manifestError,
    }),
  );
}

beforeEach(() => {
  server.use(userSessionHandler, ...dashboardHandlers);
});

describe("a manifest page", () => {
  it("shows the resource's name and its manifest in the editor", async () => {
    server.use(resourceHandler(), ...cliHandlers);
    mountAt("/secret/secrets/rMTAwx/");
    expect(await screen.findByRole("heading", { name: "example_secret" })).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Manifest YAML" })).toHaveValue(SECRET_YAML);
  });

  it("goes back to the resource's list after it is deleted", async () => {
    server.use(resourceHandler(), ...cliHandlers, ...listHandlers());
    const router = mountAt("/secret/secrets/rMTAwx/");
    const user = userEvent.setup();
    await screen.findByRole("heading", { name: "example_secret" });
    await user.click(screen.getByRole("button", { name: "Delete: Delete this Secret" }));
    await user.click(screen.getByRole("button", { name: "OK" }));
    const deleted = await screen.findByRole("dialog", { name: "Deleted" });
    await user.click(within(deleted).getAllByRole("button")[0]);
    // the list's route loads its package first.
    await waitFor(() => expect(router.state.location.pathname).toBe("/secret"));
  });

  it("is not found when the api doesn't find the resource, or the user may not read it", async () => {
    server.use(http.get(resourceUrl("secret-nope"), () => HttpResponse.json({ error: "x" }, { status: 404 })));
    mountAt("/secret/secrets/nope/");
    expect(await screen.findByRole("heading", { name: "Page not found" })).toBeInTheDocument();
  });

  it("explains a manifest that the api couldn't read, and an api that failed", async () => {
    server.use(resourceHandler(null, "The Secret example_secret has no manifest."));
    mountAt("/secret/secrets/rMTAwx/");
    expect(await screen.findByRole("alert")).toHaveTextContent("has no manifest");

    server.use(http.get(resourceUrl("secret-rMTAwx"), () => HttpResponse.json({}, { status: 500 })));
    mountAt("/secret/secrets/rMTAwx/");
    expect(await screen.findByText("The manifest could not be loaded.")).toBeInTheDocument();
  });

  it("is not found while its feature is off", async () => {
    mountAt("/proxy/proxies/rMTAwx/");
    expect(await screen.findByRole("heading", { name: "Page not found" })).toBeInTheDocument();
  });

  it("shows a feature's page while the feature is on", async () => {
    server.use(
      sessionHandler({ ...userSession, flags: { ...userSession.flags, proxy: true } }),
      http.get(resourceUrl("proxy-rMTAwx"), () =>
        HttpResponse.json({
          kind: "Proxy",
          name: "a_proxy",
          recordLocator: "proxy-rMTAwx",
          manifest: "kind: Proxy\n",
          manifestError: "",
        }),
      ),
      ...cliHandlers,
    );
    mountAt("/proxy/proxies/rMTAwx/");
    expect(await screen.findByRole("heading", { name: "a_proxy" })).toBeInTheDocument();
  });
});

describe("the manifest pages", () => {
  it("make each resource's record locator from its model's prefix and the page's id", () => {
    const secret = MANIFEST_PAGES.find((page) => page.prefix === "secret")!;
    expect(recordLocator(secret, "rMTAwx")).toBe("secret-rMTAwx");
    expect(resourceUrl("secret-rMTAwx")).toBe("/api/web/dashboard/resource/secret-rMTAwx/");
    for (const page of MANIFEST_PAGES) {
      expect(page.path).toMatch(/\/:id$/);
      expect(page.prefix).toMatch(/^[a-z]+$/);
    }
  });
});

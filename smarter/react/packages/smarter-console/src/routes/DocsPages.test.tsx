/**
 * The docs pages: public, in their own frame, with the kinds from the session, and a kind's documents from the
 * cli api.
 */
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse, type HttpHandler } from "msw";
import { createMemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";

import { server } from "@test/server";

import App from "@/App";
import type { ConsoleSession } from "@/contract.gen";
import { kindDocumentUrl, kindOf } from "@/lib/docs";
import { userSession, visitorSession } from "@/mocks/fixtures";
import { sessionHandler } from "@/mocks/handlers";
import { routes } from "@/router";

const SECRET_MANIFEST = {
  apiVersion: "smarter.sh/v1",
  kind: "Secret",
  metadata: { name: "example_secret", version: "1.0.0" },
  spec: { config: { value: "********" } },
};

const SECRET_SCHEMA = { title: "SAMSecret", type: "object", required: ["apiVersion", "kind"] };

/** The cli api answers a kind's documents, journaled, as the backend does. */
const kindDocumentHandlers = [
  http.post("/api/v1/cli/example-manifest/:kind/", () => HttpResponse.json({ data: SECRET_MANIFEST })),
  http.post("/api/v1/cli/json-schema/:kind/", () => HttpResponse.json({ data: SECRET_SCHEMA })),
];

function mountAt(path: string, session: ConsoleSession = visitorSession, ...handlers: HttpHandler[]) {
  // a later server.use() wins, so the test's own handlers come last.
  server.use(sessionHandler(session), ...kindDocumentHandlers);
  server.use(...handlers);
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  render(<App router={router} />);
  return router;
}

describe("lib/docs", () => {
  it("finds a route's kind in any case, and nothing else", () => {
    expect(kindOf("llmclient", ["LLMClient", "Secret"])).toBe("LLMClient");
    expect(kindOf("SECRET", ["LLMClient", "Secret"])).toBe("Secret");
    expect(kindOf("llmclients", ["LLMClient"])).toBeNull();
  });

  it("asks the cli api for a kind's documents by its lower-case name", () => {
    expect(kindDocumentUrl("manifest", "LLMClient")).toBe("/api/v1/cli/example-manifest/llmclient/");
    expect(kindDocumentUrl("json-schema", "LLMClient")).toBe("/api/v1/cli/json-schema/llmclient/");
  });
});

describe("the docs frame", () => {
  it("opens the example manifests at /docs/", async () => {
    const router = mountAt("/docs/");
    expect(await screen.findByRole("heading", { level: 1, name: "Smarter Manifests" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/docs/manifests");
  });

  it("offers a visitor to sign in, without sending them there", async () => {
    mountAt("/docs/manifests/");
    const nav = await screen.findByRole("navigation", { name: "Documentation" });
    expect(within(nav).getByRole("link", { name: "Sign In" })).toHaveAttribute("href", "/login");
    expect(within(nav).queryByRole("link", { name: "Dashboard" })).not.toBeInTheDocument();
  });

  it("links a signed-in user to the dashboard", async () => {
    mountAt("/docs/manifests/", userSession);
    const nav = await screen.findByRole("navigation", { name: "Documentation" });
    expect(within(nav).getByRole("link", { name: "Dashboard" })).toHaveAttribute("href", "/dashboard");
  });

  it("shows the project's tools beside a page", async () => {
    mountAt("/docs/json-schemas/");
    const tools = await screen.findByRole("complementary", { name: "Tools" });
    expect(within(tools).getByRole("link", { name: "Smarter CLI" })).toHaveAttribute("href", "https://smarter.sh/cli/");
  });

  it("has Page not found for a path it doesn't have", async () => {
    mountAt("/docs/nothing-here/");
    expect(await screen.findByRole("heading", { name: "Page not found" })).toBeInTheDocument();
  });
});

describe("the Manifests page", () => {
  it("links each kind of the session to its example manifest", async () => {
    mountAt("/docs/manifests/");
    expect(await screen.findByRole("link", { name: "LLMClient" })).toHaveAttribute("href", "/docs/manifest/llmclient");
    expect(screen.getByRole("link", { name: "ApiConnection" })).toHaveAttribute("href", "/docs/manifest/apiconnection");
    expect(screen.getByLabelText("The layout of a manifest")).toHaveTextContent("apiVersion: smarter.sh/v1");
  });

  it("opens a kind's example manifest in place", async () => {
    const user = userEvent.setup();
    const router = mountAt("/docs/manifests/");
    await user.click(await screen.findByRole("link", { name: "Secret" }));
    expect(await screen.findByRole("heading", { level: 1, name: "Secret example manifest" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/docs/manifest/secret");
  });
});

describe("the JSON Schemas page", () => {
  it("links each kind of the session to its JSON Schema", async () => {
    mountAt("/docs/json-schemas/");
    expect(await screen.findByRole("heading", { level: 1, name: "Manifest JSON Schemas" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Secret" })).toHaveAttribute("href", "/docs/json-schema/secret");
  });
});

describe("a kind's pages", () => {
  it("shows the example manifest as YAML", async () => {
    mountAt("/docs/manifest/secret/");
    expect(await screen.findByRole("heading", { level: 1, name: "Secret example manifest" })).toBeInTheDocument();
    const manifest = await screen.findByLabelText("Secret example manifest");
    expect(manifest).toHaveTextContent("apiVersion: smarter.sh/v1");
    expect(manifest).toHaveTextContent("name: example_secret");
    expect(screen.getByRole("link", { name: "Secret JSON Schema" })).toHaveAttribute(
      "href",
      "/docs/json-schema/secret",
    );
  });

  it("shows the JSON Schema as JSON", async () => {
    mountAt("/docs/json-schema/SECRET/");
    const schema = await screen.findByLabelText("Secret JSON Schema");
    expect(schema).toHaveTextContent('"title": "SAMSecret"');
    expect(screen.getByRole("link", { name: "Secret example manifest" })).toHaveAttribute(
      "href",
      "/docs/manifest/secret",
    );
  });

  it("is not found for a kind that doesn't exist, without asking the api", async () => {
    mountAt("/docs/manifest/nosuchkind/");
    expect(await screen.findByRole("heading", { name: "Page not found" })).toBeInTheDocument();
  });

  it("says so when the api fails", async () => {
    mountAt(
      "/docs/json-schema/secret/",
      visitorSession,
      http.post("/api/v1/cli/json-schema/:kind/", () => HttpResponse.json({}, { status: 500 })),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent("Secret JSON Schema couldn't be loaded.");
  });

  it("says so when the api answers without a document", async () => {
    mountAt(
      "/docs/manifest/secret/",
      visitorSession,
      http.post("/api/v1/cli/example-manifest/:kind/", () => HttpResponse.json({ message: "no data" })),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent("Secret example manifest couldn't be loaded.");
  });
});

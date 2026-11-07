/**
 * The Prompt Engineer's Workbench, /workbench/llm-clients/:id/prompt. The workbench package has its own tests; here, a
 * stand-in shows the configuration that the console gives it, so that these test the console's route, its access
 * check and the configuration.
 */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { createMemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { dashboardHandlers } from "@smarter/dashboard/mocks";
import { listHandlers } from "@smarter/llmclient-list/mocks";
import type { WorkbenchProps } from "@smarter/workbench";

import { server } from "@test/server";

import App from "@/App";
import { resourceUrl } from "@/lib/manifestPages";
import { userSession } from "@/mocks/fixtures";
import { sessionHandler } from "@/mocks/handlers";
import { routes } from "@/router";

vi.mock("@smarter/workbench", () => ({
  Workbench: ({ workbench, onboarding }: WorkbenchProps) => (
    <div>
      <pre aria-label="configuration">{JSON.stringify({ ...workbench, navigate: undefined, session: undefined })}</pre>
      <p>onboarding {onboarding ? "on" : "off"}</p>
      <button type="button" onClick={() => workbench.navigate?.(workbench.llmclientListUrl)}>
        Delete
      </button>
    </div>
  ),
}));

const LOCATOR = "llmclient-rMTAwx";

function mountAt(path: string, flags: Partial<typeof userSession.flags> = {}) {
  server.use(sessionHandler({ ...userSession, flags: { ...userSession.flags, ...flags } }));
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  render(<App router={router} />);
  return router;
}

function resourceAnswers(status: number) {
  return http.get(resourceUrl(LOCATOR), () =>
    status === 200
      ? HttpResponse.json({
          kind: "LLMClient",
          name: "stackademy",
          recordLocator: LOCATOR,
          manifest: "",
          manifestError: "",
        })
      : HttpResponse.json({ error: "Not found." }, { status }),
  );
}

async function configuration() {
  const text = (await screen.findByLabelText("configuration")).textContent ?? "";
  return JSON.parse(text) as Record<string, unknown>;
}

beforeEach(() => {
  server.use(...dashboardHandlers);
});

describe("the workbench", () => {
  it("configures the workbench from the hashed id and the session", async () => {
    server.use(resourceAnswers(200));
    mountAt("/workbench/llm-clients/rMTAwx/prompt/", { serverLogs: true });
    const config = await configuration();
    expect(config).toMatchObject({
      apiUrl: "/api/v1/llm-clients/rMTAwx/",
      toggleMetadata: true,
      sessionCookieName: "session_key",
      logStreamUrl: "/api/web/dashboard/logs/stream/",
      manifestUrl: "/api/web/prompt/llm-clients/rMTAwx/manifest/",
      architectureUrl: "/api/web/prompt/llm-clients/rMTAwx/architecture/",
      deploymentUrl: "/api/web/prompt/llm-clients/rMTAwx/deployment/",
      llmclientListUrl: "/workbench",
      applyApiUrl: "/api/v1/cli/apply/",
      validateApiUrl: "/api/v1/cli/validate/",
      deleteApiUrl: "/api/v1/cli/delete/__kind__/",
      kindPlaceholder: "__kind__",
    });
    expect(screen.getByRole("region", { name: "Chat with your AI assistant" })).toBeInTheDocument();
  });

  it("has no Server Logs tab while the server logs are off", async () => {
    server.use(resourceAnswers(200));
    mountAt("/workbench/llm-clients/rMTAwx/prompt/", { serverLogs: false });
    expect((await configuration()).logStreamUrl).toBeNull();
  });

  it("goes to the LLM Clients list with the router after a delete", async () => {
    server.use(resourceAnswers(200), ...listHandlers());
    const router = mountAt("/workbench/llm-clients/rMTAwx/prompt/");
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Delete" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/workbench"));
  });

  it("is not found for an LLMClient that the resource api refuses", async () => {
    server.use(resourceAnswers(404));
    mountAt("/workbench/llm-clients/rMTAwx/prompt/");
    expect(await screen.findByRole("heading", { name: "Page not found" })).toBeInTheDocument();
    expect(screen.queryByLabelText("configuration")).not.toBeInTheDocument();
  });

  it("says so when the LLMClient can't be loaded", async () => {
    server.use(resourceAnswers(500));
    mountAt("/workbench/llm-clients/rMTAwx/prompt/");
    expect(await screen.findByRole("alert")).toHaveTextContent("The LLMClient could not be loaded.");
  });
});

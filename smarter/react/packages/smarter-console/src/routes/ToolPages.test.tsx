/**
 * The tool pages: the manifest drop zone, the Prompt Passthrough and the Terminal. Each package has its own tests;
 * here, a stand-in of each shows what the console gives it, so that these test the console's routes, gates and
 * props.
 */
import { render, screen } from "@testing-library/react";
import { createMemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { dashboardHandlers } from "@smarter/dashboard/mocks";

import { server } from "@test/server";

import App from "@/App";
import type { ConsoleSession } from "@/contract.gen";
import { userSession } from "@/mocks/fixtures";
import { sessionHandler } from "@/mocks/handlers";
import { routes } from "@/router";

interface StandInProps {
  sessionContext: { ApiUrl: string };
  providerApiUrl?: string;
  logStreamUrl?: string;
}

vi.mock("@smarter/drop-zone", () => ({
  ManifestDropzone: ({ sessionContext }: StandInProps) => <p>drop zone at {sessionContext.ApiUrl}</p>,
}));
vi.mock("@smarter/prompt-passthrough", () => ({
  PromptPassthrough: ({ sessionContext, providerApiUrl, logStreamUrl }: StandInProps) => (
    <p>
      passthrough at {sessionContext.ApiUrl}, providers at {providerApiUrl}, logs at [{logStreamUrl}]
    </p>
  ),
}));
vi.mock("@smarter/terminal-emulator", () => ({
  TerminalEmulator: ({ sessionContext }: StandInProps) => <p>terminal at {sessionContext.ApiUrl}</p>,
}));

function mountAt(path: string, flags: Partial<ConsoleSession["flags"]> = {}) {
  server.use(sessionHandler({ ...userSession, flags: { ...userSession.flags, ...flags } }));
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  render(<App router={router} />);
  return router;
}

beforeEach(() => {
  server.use(...dashboardHandlers);
});

describe("the manifest drop zone", () => {
  it("applies with the cli api while its feature is on", async () => {
    mountAt("/dashboard/dropzone/", { manifestDropZone: true });
    expect(await screen.findByText("drop zone at /api/v1/cli/apply/")).toBeInTheDocument();
  });

  it("is not found while its feature is off", async () => {
    mountAt("/dashboard/dropzone/", { manifestDropZone: false });
    expect(await screen.findByRole("heading", { name: "Page not found" })).toBeInTheDocument();
  });
});

describe("the Prompt Passthrough", () => {
  it("calls the passthrough api, with the server logs while they are on", async () => {
    mountAt("/dashboard/passthrough/", { passthrough: true, serverLogs: true });
    expect(
      await screen.findByText(
        "passthrough at /api/v1/prompts/passthrough/, providers at /api/web/dashboard/passthrough/providers/, logs at [/api/web/dashboard/logs/stream/]",
      ),
    ).toBeInTheDocument();
  });

  it("has no log stream while the server logs are off", async () => {
    mountAt("/dashboard/passthrough/", { passthrough: true, serverLogs: false });
    expect(await screen.findByText(/logs at \[\]/)).toBeInTheDocument();
  });

  it("is not found while its feature is off", async () => {
    mountAt("/dashboard/passthrough/", { passthrough: false });
    expect(await screen.findByRole("heading", { name: "Page not found" })).toBeInTheDocument();
  });
});

describe("the Terminal", () => {
  it("opens with the ticket api for a superuser while it is on", async () => {
    mountAt("/dashboard/terminal/", { terminal: true });
    expect(await screen.findByText("terminal at /api/web/dashboard/terminal/ticket/")).toBeInTheDocument();
  });

  it("is not found while it is off, as it is for everyone but a superuser", async () => {
    mountAt("/dashboard/terminal/", { terminal: false });
    expect(await screen.findByRole("heading", { name: "Page not found" })).toBeInTheDocument();
  });
});

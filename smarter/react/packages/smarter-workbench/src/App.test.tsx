import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "@/App";
import { FakeEventSource, installFakes } from "@/mocks/fakes";
import { CONFIG_URL, LOG_STREAM_URL, configWithHistory, leanConfig, plainWorkbench, workbench } from "@/mocks/fixtures";
import { chatHandlers, tabHandlers } from "@/mocks/handlers";
import { server } from "@test/server";

vi.mock("@smarter/manifest-editor", async () => await import("@/mocks/ManifestEditor"));

const WELCOME = "Welcome to Stackademy! How can I help you today?";

/** The config api's requests, as whether each asked for the diagnostic parts, with ?verbose=true. */
function recordConfigRequests(): boolean[] {
  const requests: boolean[] = [];
  server.use(
    http.post(CONFIG_URL, ({ request }) => {
      const verbose = new URL(request.url).searchParams.get("verbose") === "true";
      requests.push(verbose);
      return HttpResponse.json({ data: verbose ? configWithHistory : leanConfig(configWithHistory) });
    }),
  );
  return requests;
}

describe("App", () => {
  beforeEach(() => {
    document.cookie = "csrftoken=the-csrf-token; path=/";
    server.use(...chatHandlers, ...tabHandlers);
  });

  it("puts the chat beside the Console, whose Config tab asks the chat for the diagnostic parts", async () => {
    const requests = recordConfigRequests();
    render(<App workbench={plainWorkbench} />);
    expect(await screen.findByText(WELCOME)).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Console" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Config" })).toHaveAttribute("aria-pressed", "true");
    await waitFor(() => expect(requests).toContain(true));
    // the Console displays the configuration that the chat fetched.
    expect(await screen.findByText("llmclient")).toBeInTheDocument();
  });

  it("asks for the diagnostic parts only while the Console displays them", async () => {
    installFakes();
    const requests = recordConfigRequests();
    const user = userEvent.setup();
    render(<App workbench={{ ...plainWorkbench, logStreamUrl: LOG_STREAM_URL }} />);
    await screen.findByText(WELCOME);
    // the server logs are selected: the configuration is lean.
    expect(requests).toEqual([false]);
    await user.click(screen.getByRole("button", { name: "Tool Calls" }));
    await waitFor(() => expect(requests).toEqual([false, true]));
    expect(await screen.findByText("stackademy_sql")).toBeInTheDocument();
    vi.unstubAllGlobals();
  });

  it("opens and closes the Docs dialog, whose button is only in sandbox mode", async () => {
    const user = userEvent.setup();
    render(<App workbench={plainWorkbench} />);
    await screen.findByText(WELCOME);
    await user.click(screen.getByRole("button", { name: "Docs" }));
    expect(screen.getByRole("dialog", { name: "Docs" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Close" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Sandbox mode" }));
    expect(screen.queryByRole("button", { name: "Docs" })).not.toBeInTheDocument();
  });

  it("hides the Console and its button in production mode, and restores them in sandbox mode", async () => {
    const user = userEvent.setup();
    render(<App workbench={plainWorkbench} />);
    await screen.findByText(WELCOME);
    expect(screen.getByRole("button", { name: "Show the Console" })).toHaveAttribute("aria-pressed", "true");

    await user.click(screen.getByRole("button", { name: "Sandbox mode" }));
    expect(screen.queryByRole("navigation", { name: "Console" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Show the Console" })).not.toBeInTheDocument();
    expect(screen.queryByRole("separator")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Production mode" }));
    expect(screen.getByRole("navigation", { name: "Console" })).toBeInTheDocument();
  });

  it("hides and shows the Console, and remembers it", async () => {
    const user = userEvent.setup();
    const { unmount } = render(<App workbench={plainWorkbench} />);
    await screen.findByText(WELCOME);
    const toggle = screen.getByRole("button", { name: "Show the Console" });
    expect(screen.getByRole("separator", { name: "Resize the chat and the Console" })).toBeInTheDocument();

    await user.click(toggle);
    expect(toggle).toHaveAttribute("aria-pressed", "false");
    expect(screen.queryByRole("navigation", { name: "Console" })).not.toBeInTheDocument();
    expect(screen.queryByRole("separator")).not.toBeInTheDocument();
    unmount();

    render(<App workbench={plainWorkbench} />);
    await screen.findByText(WELCOME);
    expect(screen.queryByRole("navigation", { name: "Console" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Show the Console" }));
    expect(screen.getByRole("navigation", { name: "Console" })).toBeInTheDocument();
  });

  it("resizes the chat with the separator", async () => {
    render(<App workbench={plainWorkbench} />);
    await screen.findByText(WELCOME);
    const separator = screen.getByRole("separator", { name: "Resize the chat and the Console" });
    expect(screen.getByRole("separator", { value: { now: 33 } })).toBe(separator);
    fireEvent.keyDown(separator, { key: "ArrowRight" });
    expect(screen.getByRole("separator", { value: { now: 38 } })).toBe(separator);
  });

  it("reloads the chat's configuration when the Manifest tab saves the manifest, and the chat continues", async () => {
    const user = userEvent.setup();
    render(<App workbench={{ ...plainWorkbench, manifestUrl: workbench.manifestUrl }} />);
    expect(await screen.findByText("Stackademy v1.0.0")).toBeInTheDocument();
    const renamed = { ...configWithHistory, llmclient: { ...configWithHistory.llmclient, app_name: "Renamed" } };
    server.use(http.post(CONFIG_URL, () => HttpResponse.json({ data: renamed })));
    await user.click(screen.getByRole("button", { name: "Manifest" }));
    await user.click(await screen.findByRole("button", { name: "Save" }));
    expect(await screen.findByText("Renamed v1.0.0")).toBeInTheDocument();
    expect(screen.getByText(WELCOME)).toBeInTheDocument();
  });

  it("clears the Console's server logs when a new chat starts, and streams the new chat session's", async () => {
    installFakes();
    const user = userEvent.setup();
    render(<App workbench={{ ...plainWorkbench, logStreamUrl: LOG_STREAM_URL }} />);
    await screen.findByText(WELCOME);
    await waitFor(() => expect(FakeEventSource.instances.length).toBeGreaterThan(0));
    // sandbox mode streams DEBUG and above.
    expect(FakeEventSource.latest().url).toContain("level=DEBUG");
    const streams = FakeEventSource.instances.length;
    await user.click(screen.getByRole("button", { name: "Start a new chat" }));
    await screen.findByText(WELCOME);
    expect(screen.getByRole("log", { name: "Console output" })).toHaveTextContent(
      "Connecting to the server log stream...",
    );

    // production mode streams the server's own log level.
    await user.click(screen.getByRole("button", { name: "Sandbox mode" }));
    await user.click(screen.getByRole("button", { name: "Production mode" }));
    expect(FakeEventSource.instances.length).toBeGreaterThan(streams);
    vi.unstubAllGlobals();
  });
});

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { FakeEventSource, installFakes } from "@smarter/serverlogs/fakes";

import App from "@/App";
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

  it("opens and closes the Docs dialog from the Help menu, which is only in sandbox mode", async () => {
    const user = userEvent.setup();
    render(<App workbench={plainWorkbench} />);
    await screen.findByText(WELCOME);
    await user.click(screen.getByRole("button", { name: "Help" }));
    await user.click(screen.getByRole("button", { name: "Technical references" }));
    expect(screen.getByRole("dialog", { name: "Docs" })).toBeInTheDocument();
    // the menu closed as the dialog opened.
    expect(screen.queryByRole("button", { name: "Technical references" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Close" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Production" }));
    expect(screen.queryByRole("button", { name: "Help" })).not.toBeInTheDocument();
  });

  it("has the guided tour, but no Docs, in its Help menu without the mode switch", async () => {
    const user = userEvent.setup();
    render(<App workbench={{ ...plainWorkbench, toggleMetadata: false }} />);
    await screen.findByText(WELCOME);
    await user.click(screen.getByRole("button", { name: "Help" }));
    expect(screen.getByRole("button", { name: "Take the guided tour" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Technical references" })).not.toBeInTheDocument();
  });

  it("hides the Console and its button in production mode, and restores them in sandbox mode", async () => {
    const user = userEvent.setup();
    render(<App workbench={plainWorkbench} />);
    await screen.findByText(WELCOME);
    expect(screen.getByRole("button", { name: "Show the Console" })).toHaveAttribute("aria-pressed", "true");

    await user.click(screen.getByRole("button", { name: "Production" }));
    expect(screen.queryByRole("navigation", { name: "Console" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Show the Console" })).not.toBeInTheDocument();
    expect(screen.queryByRole("separator")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Sandbox" }));
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

  /** Lays every element out with a size, so that the tour finds the parts that it points to. jsdom has no layout. */
  function layOutThePage() {
    vi.spyOn(Element.prototype, "getBoundingClientRect").mockReturnValue({
      top: 100,
      left: 100,
      width: 120,
      height: 40,
      x: 100,
      y: 100,
      right: 220,
      bottom: 140,
      toJSON: () => ({}),
    } as DOMRect);
  }

  const onboarding = {
    enabled: true,
    apiUrl: "/dashboard/api/onboarding/seen/",
    seen: [],
    csrfCookieName: "csrftoken",
    cookieDomain: "localhost",
  };

  it("takes the guided tour from the Help menu, which opens the Console first", async () => {
    layOutThePage();
    const user = userEvent.setup();
    render(<App workbench={plainWorkbench} onboarding={null} />);
    await screen.findByText(WELCOME);
    await user.click(screen.getByRole("button", { name: "Show the Console" }));
    expect(screen.queryByRole("navigation", { name: "Console" })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Help" }));
    await user.click(screen.getByRole("button", { name: "Take the guided tour" }));
    expect(
      await screen.findByRole("dialog", { name: "Welcome to the Prompt Engineer's Workbench" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Console" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.getByRole("dialog", { name: "The chat" })).toBeInTheDocument();
    // the Console's Manifest tab, among others, isn't on this page: the tour leaves its step out.
    for (let step = 0; step < 4; step++) await user.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.getByRole("dialog", { name: "Tool calls" })).toBeInTheDocument();
    // the step selects the tab that it is about, so that the Console shows its content.
    expect(screen.getByRole("button", { name: "Tool Calls" })).toHaveAttribute("aria-pressed", "true");
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("starts the tour by itself once the chat is ready, and records it, once", async () => {
    layOutThePage();
    const posted: unknown[] = [];
    server.use(
      http.post(onboarding.apiUrl, async ({ request }) => {
        posted.push(await request.json());
        return HttpResponse.json({ seen: ["workbench_tour"] });
      }),
    );
    const user = userEvent.setup();
    render(<App workbench={plainWorkbench} onboarding={onboarding} />);
    await user.click(await screen.findByRole("button", { name: "Skip tour" }, { timeout: 3000 }));
    await waitFor(() => expect(posted).toEqual([{ hint: "workbench_tour", outcome: "dismissed" }]));
    await user.click(screen.getByRole("button", { name: "Help" }));
    await user.click(screen.getByRole("button", { name: "Take the guided tour" }));
    await user.click(await screen.findByRole("button", { name: "Skip tour" }));
    expect(posted).toHaveLength(1);
  });

  it("doesn't start the tour by itself for a user who has taken it", async () => {
    layOutThePage();
    render(<App workbench={plainWorkbench} onboarding={{ ...onboarding, seen: ["workbench_tour"] }} />);
    await screen.findByText(WELCOME);
    await new Promise((resolve) => setTimeout(resolve, 600));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
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
    await user.click(screen.getByRole("button", { name: "Production" }));
    await user.click(screen.getByRole("button", { name: "Sandbox" }));
    expect(FakeEventSource.instances.length).toBeGreaterThan(streams);
    vi.unstubAllGlobals();
  });
});

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { appContext, welcome } from "@/mocks/fixtures";
import { server } from "@test/server";

import App, { OPEN_ATTRIBUTE } from "@/App";

/** Answers both welcome apis, and records the dismiss api's request bodies. */
function useWelcomeApis(dismissStatus = 200) {
  const dismissed = vi.fn();
  server.use(
    http.post(appContext.apiUrl, () => HttpResponse.json(welcome)),
    http.post(appContext.dismissApiUrl, async ({ request }) => {
      const body = (await request.json()) as { showAtStartup: boolean };
      dismissed(body);
      return HttpResponse.json({ ...welcome, welcomed: !body.showAtStartup }, { status: dismissStatus });
    }),
  );
  return dismissed;
}

describe("App", () => {
  it("spotlights the sidebar's LLM Clients link once the dialog is closed, not while it is open", async () => {
    const user = userEvent.setup();
    useWelcomeApis();
    server.use(http.post("/dashboard/api/onboarding/seen/", () => HttpResponse.json({ seen: [] })));
    const link = document.createElement("a");
    link.href = "/workbench/";
    link.setAttribute("data-smarter-onboarding", "sidebar-llmclients");
    document.body.append(link);
    vi.spyOn(link, "getBoundingClientRect").mockReturnValue({
      top: 200,
      left: 20,
      width: 200,
      height: 40,
      x: 20,
      y: 200,
      right: 220,
      bottom: 240,
      toJSON: () => ({}),
    } as DOMRect);
    const onboarding = {
      enabled: true,
      apiUrl: "/dashboard/api/onboarding/seen/",
      seen: [],
      csrfCookieName: "csrftoken",
      cookieDomain: "localhost",
    };
    render(<App appContext={{ ...appContext, onboarding }} />);
    expect(screen.queryByRole("button", { name: "Got it" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Skip tour" }));
    expect(await screen.findByRole("dialog", { name: "Start building your AI masterpiece here." })).toBeInTheDocument();
    link.remove();
  });

  it("opens by itself for a user who hasn't been welcomed, and records it when closed", async () => {
    const user = userEvent.setup();
    const dismissed = useWelcomeApis();
    render(<App appContext={appContext} />);
    expect(screen.getByRole("dialog", { name: "Welcome to Smarter, Ada!" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Skip tour" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    await waitFor(() => expect(dismissed).toHaveBeenCalledTimes(1));
    // Show at startup is ticked for a new user: the dialog opens again when they next sign in.
    expect(dismissed).toHaveBeenCalledWith({ showAtStartup: true });
  });

  it("records an unticked Show at startup box, so that it no longer opens by itself", async () => {
    const user = userEvent.setup();
    const dismissed = useWelcomeApis();
    render(<App appContext={appContext} />);
    await user.click(screen.getByRole("checkbox", { name: "Show at startup" }));
    await user.click(screen.getByRole("button", { name: "Close" }));
    await waitFor(() => expect(dismissed).toHaveBeenCalledWith({ showAtStartup: false }));
  });

  it("records a box ticked again from the user menu, and nothing when it is unchanged", async () => {
    const user = userEvent.setup();
    const dismissed = useWelcomeApis();
    render(
      <>
        <button type="button" {...{ [OPEN_ATTRIBUTE]: "true" }}>
          Welcome Tour
        </button>
        <App appContext={{ ...appContext, show: false, showAtStartup: false }} />
      </>,
    );
    const menuItem = screen.getByRole("button", { name: "Welcome Tour" });
    await user.click(menuItem);
    expect(screen.getByRole("checkbox", { name: "Show at startup" })).not.toBeChecked();
    await user.keyboard("{Escape}");
    expect(dismissed).not.toHaveBeenCalled();
    await user.click(menuItem);
    await user.click(screen.getByRole("checkbox", { name: "Show at startup" }));
    await user.click(screen.getByRole("button", { name: "Close" }));
    await waitFor(() => expect(dismissed).toHaveBeenCalledWith({ showAtStartup: true }));
    await user.click(menuItem);
    expect(screen.getByRole("checkbox", { name: "Show at startup" })).toBeChecked();
    await user.keyboard("{Escape}");
    expect(dismissed).toHaveBeenCalledTimes(1);
  });

  it("records it once the last step shows, before the user follows a link", async () => {
    const user = userEvent.setup();
    const dismissed = useWelcomeApis();
    render(<App appContext={appContext} />);
    await user.click(screen.getByRole("button", { name: "Go to step 8" }));
    expect(await screen.findByRole("link", { name: /Try the Get Weather LLMClient/ })).toBeInTheDocument();
    await waitFor(() => expect(dismissed).toHaveBeenCalledTimes(1));
    await user.click(screen.getByRole("button", { name: "Get started" }));
    expect(dismissed).toHaveBeenCalledTimes(1);
  });

  it("stays closed for a user who has been welcomed, until they open it from the user menu", async () => {
    const user = userEvent.setup();
    const dismissed = useWelcomeApis();
    render(
      <>
        <button type="button" {...{ [OPEN_ATTRIBUTE]: "true" }}>
          Welcome Tour
        </button>
        <App appContext={{ ...appContext, show: false }} />
      </>,
    );
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    const menuItem = screen.getByRole("button", { name: "Welcome Tour" });
    menuItem.focus();
    await user.click(menuItem);
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(menuItem).toHaveFocus();
    expect(dismissed).not.toHaveBeenCalled();
  });

  it("ignores clicks elsewhere on the page", async () => {
    const user = userEvent.setup();
    useWelcomeApis();
    render(
      <>
        <button type="button">Elsewhere</button>
        <App appContext={{ ...appContext, show: false }} />
      </>,
    );
    await user.click(screen.getByRole("button", { name: "Elsewhere" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("shows why the links failed to load", async () => {
    const user = userEvent.setup();
    vi.spyOn(console, "error").mockImplementation(() => {});
    server.use(http.post(appContext.apiUrl, () => new HttpResponse(null, { status: 503 })));
    render(<App appContext={appContext} />);
    await user.click(screen.getByRole("button", { name: "Go to step 8" }));
    expect(await screen.findByText("Failed to load the links: Request failed: 503")).toBeInTheDocument();
  });

  it("tries to record it again after a failed dismiss request", async () => {
    const user = userEvent.setup();
    vi.spyOn(console, "error").mockImplementation(() => {});
    const dismissed = useWelcomeApis(500);
    render(
      <>
        <button type="button" {...{ [OPEN_ATTRIBUTE]: "true" }}>
          Welcome Tour
        </button>
        <App appContext={appContext} />
      </>,
    );
    await user.click(screen.getByRole("button", { name: "Close" }));
    await waitFor(() => expect(dismissed).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(console.error).toHaveBeenCalled());
    await user.click(screen.getByRole("button", { name: "Welcome Tour" }));
    await user.click(screen.getByRole("button", { name: "Close" }));
    await waitFor(() => expect(dismissed).toHaveBeenCalledTimes(2));
  });
});

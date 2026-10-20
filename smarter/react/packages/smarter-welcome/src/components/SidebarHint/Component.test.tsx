import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { server } from "@test/server";
import { useOnboarding, type OnboardingContext } from "@smarter/onboarding";

import SidebarHint from "@/components/SidebarHint/Component";

const context: OnboardingContext = {
  enabled: true,
  apiUrl: "/dashboard/api/onboarding/seen/",
  seen: [],
  csrfCookieName: "csrftoken",
  cookieDomain: "localhost",
};

function Hint({ onboarding }: { onboarding: OnboardingContext }) {
  return <SidebarHint onboarding={useOnboarding(onboarding)} />;
}

const links: HTMLAnchorElement[] = [];

/** The sidebar's LLM Clients link, laid out on the page. */
function addLink(href = "/workbench/") {
  const link = document.createElement("a");
  link.href = href;
  link.textContent = "LLM Clients";
  link.setAttribute("data-smarter-onboarding", "sidebar-llmclients");
  document.body.append(link);
  links.push(link);
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
  return link;
}

describe("SidebarHint", () => {
  let posted: unknown[];
  beforeEach(() => {
    posted = [];
    server.use(
      http.post(context.apiUrl, async ({ request }) => {
        posted.push(await request.json());
        return HttpResponse.json({ seen: [] });
      }),
    );
  });
  afterEach(() => {
    for (const link of links.splice(0)) link.remove();
    window.history.pushState({}, "", "/");
  });

  it("spotlights the sidebar's LLM Clients link, and records the click on it", async () => {
    const link = addLink();
    render(<Hint onboarding={context} />);
    expect(await screen.findByRole("dialog", { name: "Start building your AI masterpiece here." })).toBeInTheDocument();
    fireEvent.click(link);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    await waitFor(() => expect(posted).toEqual([{ hint: "sidebar_llmclients", outcome: "clicked" }]));
  });

  it("is dismissed with Got it", async () => {
    const user = userEvent.setup();
    addLink();
    render(<Hint onboarding={context} />);
    await user.click(await screen.findByRole("button", { name: "Got it" }));
    await waitFor(() => expect(posted).toEqual([{ hint: "sidebar_llmclients", outcome: "dismissed" }]));
  });

  it("records a user who is already among their LLMClients as visited, without showing", async () => {
    addLink("/workbench/");
    window.history.pushState({}, "", "/workbench/llm-clients/3f2a9c/prompt/");
    render(<Hint onboarding={context} />);
    await waitFor(() => expect(posted).toEqual([{ hint: "sidebar_llmclients", outcome: "visited" }]));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("shows nothing once seen, or without the link", () => {
    addLink();
    const { unmount } = render(<Hint onboarding={{ ...context, seen: ["sidebar_llmclients"] }} />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    unmount();
    for (const link of links.splice(0)) link.remove();
    render(<Hint onboarding={context} />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(posted).toEqual([]);
  });
});

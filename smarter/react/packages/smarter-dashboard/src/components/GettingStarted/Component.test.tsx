import { render, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { afterEach, describe, expect, it, vi } from "vitest";

import { appContext } from "@/mocks/fixtures";
import { server } from "@test/server";

import GettingStarted from "@/components/GettingStarted/Component";

const apiUrl = appContext.gettingStartedApiUrl;
const COOKIE = "smarter_getting_started_done";
const DAY_MS = 24 * 60 * 60 * 1000;

function steps(...done: boolean[]) {
  return {
    steps: done.map((isDone, index) => ({
      name: `Step ${index + 1}`,
      description: `Do step ${index + 1}.`,
      done: isDone,
      url: "/workbench/",
    })),
  };
}

function respond(body: object) {
  server.use(http.post(apiUrl, () => HttpResponse.json(body)));
}

function setDoneCookie(daysAgo: number) {
  document.cookie = `${COOKIE}=${new Date(Date.now() - daysAgo * DAY_MS).toISOString()}; path=/`;
}

function doneCookie(): string | undefined {
  return document.cookie
    .split(";")
    .map((cookie) => cookie.trim())
    .find((cookie) => cookie.startsWith(`${COOKIE}=`));
}

function renderGettingStarted() {
  render(<GettingStarted sessionContext={appContext.sessionContext} apiUrl={apiUrl} />);
}

describe("GettingStarted", () => {
  afterEach(() => {
    document.cookie = `${COOKIE}=; path=/; expires=${new Date(0).toUTCString()}`;
  });

  it("shows every step to a user who has done none of them", async () => {
    respond(steps(false, false, false, false));
    renderGettingStarted();
    expect(await screen.findByText("0 of 4 steps done")).toBeInTheDocument();
    expect(screen.getAllByLabelText("to do")).toHaveLength(4);
    expect(doneCookie()).toBeUndefined();
  });

  it("numbers the steps left to do, and checks off the done ones", async () => {
    respond(steps(true, false, false));
    renderGettingStarted();
    expect(await screen.findByText("1 of 3 steps done")).toBeInTheDocument();
    expect(screen.getByLabelText("done")).toBeInTheDocument();
    expect(screen.getAllByLabelText("to do").map((step) => step.textContent)).toEqual(["2", "3"]);
  });

  it("keeps showing once every step is done, and remembers when in a cookie", async () => {
    respond(steps(true, true, true));
    renderGettingStarted();
    expect(await screen.findByText("All 3 steps done. Nice work!")).toBeInTheDocument();
    await waitFor(() => expect(doneCookie()).toBeDefined());
  });

  it("keeps showing for 90 days after every step was done, and renews the cookie", async () => {
    setDoneCookie(89);
    const before = doneCookie();
    respond(steps(true, true));
    renderGettingStarted();
    expect(await screen.findByText("All 2 steps done. Nice work!")).toBeInTheDocument();
    expect(doneCookie()).toBe(before);
  });

  it("hides itself more than 90 days after every step was done", async () => {
    setDoneCookie(91);
    const request = vi.fn();
    server.use(
      http.post(apiUrl, () => {
        request();
        return HttpResponse.json(steps(true, true));
      }),
    );
    renderGettingStarted();
    await waitFor(() => expect(request).toHaveBeenCalled());
    await waitFor(() => expect(screen.queryByRole("region", { name: "Getting Started" })).not.toBeInTheDocument());
  });

  it("shows why the steps failed to load, rather than disappearing", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    server.use(http.post(apiUrl, () => new HttpResponse(null, { status: 500 })));
    renderGettingStarted();
    expect(
      await screen.findByText("Failed to load the getting started steps: Request failed: 500"),
    ).toBeInTheDocument();
  });
});

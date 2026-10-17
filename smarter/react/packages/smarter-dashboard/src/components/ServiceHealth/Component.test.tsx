import { fireEvent, render, screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { appContext, serviceHealth } from "@/mocks/fixtures";
import { server } from "@test/server";

import ServiceHealth from "@/components/ServiceHealth/Component";

const apiUrl = appContext.serviceHealthApiUrl;

function renderWith(data: typeof serviceHealth) {
  server.use(http.post(apiUrl, () => HttpResponse.json(data)));
  return render(<ServiceHealth sessionContext={appContext.sessionContext} apiUrl={apiUrl} />);
}

function withHealth(healthy: boolean[]) {
  const health_checks = serviceHealth.health_checks.map((check, i) => ({ ...check, healthy: healthy[i] }));
  const health_score = Math.round((healthy.filter(Boolean).length / healthy.length) * 100);
  return { ...serviceHealth, health_checks, health_score };
}

describe("ServiceHealth", () => {
  it("shows the platform's version, distribution and runtime", async () => {
    renderWith(serviceHealth);
    expect(await screen.findByText("Smarter v0.18.0 on Debian GNU/Linux 13")).toBeInTheDocument();
    const runtime = screen.getByRole("list", { name: "Runtime versions" });
    expect(runtime).toHaveTextContent("Python3.14.0");
    expect(runtime).toHaveTextContent("DRF3.16.1");
    expect(runtime).toHaveAttribute("title", "Python 3.14.0 · Django 6.0.8 · Pydantic 2.13.5 · DRF 3.16.1");
  });

  it("marks each check healthy or down", async () => {
    renderWith(serviceHealth);
    const checks = await screen.findByRole("list", { name: "Backend services" });
    expect(within(checks).getAllByRole("listitem")).toHaveLength(4);
    expect(within(checks).getByRole("listitem", { name: "Database" })).toHaveTextContent("Healthy");
    const workers = within(checks).getByRole("listitem", { name: "Workers" });
    expect(workers).toHaveTextContent("Down");
    expect(workers).toHaveClass("service-health-check-down");
  });

  it("explains what each check tests in its tooltip", async () => {
    renderWith(serviceHealth);
    const checks = await screen.findByRole("list", { name: "Backend services" });
    expect(within(checks).getByRole("listitem", { name: "Workers" })).toHaveAttribute(
      "title",
      "Workers: At least one Celery worker, which runs background jobs, answers a ping.",
    );
    expect(screen.getByText("Backend services")).toHaveAttribute("title", expect.stringMatching(/^Live checks/));
  });

  it("is green when every check passes", async () => {
    renderWith(withHealth([true, true, true, true]));
    expect(await screen.findByText("All systems operational")).toHaveClass("badge-light-success");
    expect(screen.getByRole("img", { name: "Service health 100 percent" })).toHaveClass("service-health-ring-healthy");
  });

  it("is amber when at least half of the checks pass", async () => {
    renderWith(serviceHealth);
    expect(await screen.findByText("1 of 4 checks failing")).toHaveClass("badge-light-warning");
    expect(screen.getByRole("img", { name: "Service health 75 percent" })).toHaveClass("service-health-ring-degraded");
  });

  it("is red when fewer than half of the checks pass", async () => {
    renderWith(withHealth([false, false, false, true]));
    expect(await screen.findByText("3 of 4 checks failing")).toHaveClass("badge-light-danger");
    expect(screen.getByRole("img", { name: "Service health 25 percent" })).toHaveClass("service-health-ring-down");
  });

  it("says check, not checks, when there is only one", async () => {
    renderWith({ ...serviceHealth, health_checks: [{ name: "Database", healthy: false }], health_score: 0 });
    expect(await screen.findByText("1 of 1 check failing")).toBeInTheDocument();
  });

  it("gives a check it doesn't know a generic icon", async () => {
    renderWith({ ...serviceHealth, health_checks: [{ name: "Search", healthy: true }], health_score: 100 });
    const search = await screen.findByRole("listitem", { name: "Search" });
    expect(within(search).getByTestId("check-icon")).toHaveClass("ki-abstract-26");
    expect(search).toHaveAttribute("title", "Search");
  });

  it("links the badges to the platform's own repository", async () => {
    renderWith({ ...serviceHealth, repository_url: "https://github.com/someone/smarter" });
    const badges = await screen.findByRole("list", { name: "Build status" });
    expect(within(badges).getByRole("link", { name: "Build Status" })).toHaveAttribute(
      "href",
      "https://github.com/someone/smarter/actions/workflows/build.yml",
    );
    expect(within(badges).getByRole("img", { name: "Build Status" })).toHaveAttribute(
      "src",
      "https://github.com/someone/smarter/actions/workflows/build.yml/badge.svg?branch=main",
    );
  });

  it("tries the badges of a repository on any host", async () => {
    renderWith({ ...serviceHealth, repository_url: "https://bitbucket.org/someone/smarter" });
    const badges = await screen.findByRole("list", { name: "Build status" });
    expect(within(badges).getByRole("link", { name: "Test Status" })).toHaveAttribute(
      "href",
      "https://bitbucket.org/someone/smarter/actions/workflows/test.yml",
    );
  });

  it("says the CI status is unknown when the repository url isn't safe to link to", async () => {
    renderWith({ ...serviceHealth, repository_url: "javascript:alert(1)" });
    expect(await screen.findByText("CI status unknown")).toBeInTheDocument();
    expect(screen.queryByRole("list", { name: "Build status" })).not.toBeInTheDocument();
  });

  it("leaves out a badge that fails to load", async () => {
    renderWith(serviceHealth);
    const badges = await screen.findByRole("list", { name: "Build status" });
    fireEvent.error(within(badges).getByRole("img", { name: "Release Status" }));
    expect(within(badges).queryByRole("img", { name: "Release Status" })).not.toBeInTheDocument();
    expect(within(badges).getAllByRole("img")).toHaveLength(2);
  });

  it("says the CI status is unknown when no badge loads", async () => {
    renderWith(serviceHealth);
    const badges = await screen.findByRole("list", { name: "Build status" });
    for (const name of ["Build Status", "Test Status", "Release Status"]) {
      fireEvent.error(within(badges).getByRole("img", { name }));
    }
    expect(await screen.findByText("CI status unknown")).toBeInTheDocument();
  });

  it("links the CI badges", async () => {
    renderWith(serviceHealth);
    const badges = await screen.findByRole("list", { name: "Build status" });
    expect(within(badges).getByRole("link", { name: "Test Status" })).toHaveAttribute(
      "href",
      "https://github.com/smarter-sh/smarter/actions/workflows/test.yml",
    );
    expect(within(badges).getAllByRole("link")).toHaveLength(3);
    expect(within(badges).queryByRole("link", { name: "Codecov" })).not.toBeInTheDocument();
  });

  it("doesn't animate the ring when the score is the one it showed last", async () => {
    window.localStorage.setItem("smarter_service_health_ring", "75");
    const frame = vi.spyOn(window, "requestAnimationFrame");
    renderWith(serviceHealth);
    expect(await screen.findByRole("img", { name: "Service health 75 percent" })).toHaveTextContent("75%");
    expect(frame).not.toHaveBeenCalled();
  });

  it("animates the ring from the score it showed last to a new one", async () => {
    window.localStorage.setItem("smarter_service_health_ring", "100");
    renderWith(serviceHealth);
    const ring = await screen.findByRole("img", { name: "Service health 75 percent" });
    expect(ring).not.toHaveTextContent(/^0%/);
    // jsdom runs animation frames slower than a browser.
    await vi.waitFor(() => expect(ring).toHaveTextContent("75%"), { timeout: 3000 });
    expect(window.localStorage.getItem("smarter_service_health_ring")).toBe("75");
  });

  it("still shows the ring when storage is blocked", async () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new DOMException("blocked", "SecurityError");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("blocked", "SecurityError");
    });
    renderWith(serviceHealth);
    const ring = await screen.findByRole("img", { name: "Service health 75 percent" });
    // jsdom runs animation frames slower than a browser.
    await vi.waitFor(() => expect(ring).toHaveTextContent("75%"), { timeout: 3000 });
  });

  it("shows the last response on the next page load, without asking again or animating", async () => {
    let requests = 0;
    server.use(
      http.post(apiUrl, () => {
        requests += 1;
        return HttpResponse.json(serviceHealth);
      }),
    );
    const { unmount } = render(<ServiceHealth sessionContext={appContext.sessionContext} apiUrl={apiUrl} />);
    await screen.findByRole("list", { name: "Backend services" });
    unmount();

    const frame = vi.spyOn(window, "requestAnimationFrame");
    render(<ServiceHealth sessionContext={appContext.sessionContext} apiUrl={apiUrl} />);
    expect(screen.getByRole("img", { name: "Service health 75 percent" })).toHaveTextContent("75%");
    expect(frame).not.toHaveBeenCalled();
    expect(requests).toBe(1);
  });

  it("shows the ring's final value at once when the user prefers reduced motion", async () => {
    const matchMedia = vi.fn().mockReturnValue({ matches: true });
    vi.stubGlobal("matchMedia", matchMedia);
    renderWith(serviceHealth);
    const ring = await screen.findByRole("img", { name: "Service health 75 percent" });
    expect(ring).toHaveTextContent("75%");
    expect(matchMedia).toHaveBeenCalledWith("(prefers-reduced-motion: reduce)");
    vi.unstubAllGlobals();
  });

  it("runs the checks again when the refresh button is pressed", async () => {
    const bodies: unknown[] = [];
    server.use(
      http.post(apiUrl, async ({ request }) => {
        bodies.push(await request.json());
        return HttpResponse.json(bodies.length === 1 ? serviceHealth : withHealth([true, true, true, true]));
      }),
    );
    render(<ServiceHealth sessionContext={appContext.sessionContext} apiUrl={apiUrl} />);
    expect(await screen.findByText("1 of 4 checks failing")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Refresh service health" }));
    expect(await screen.findByText("All systems operational")).toBeInTheDocument();
    expect(bodies).toEqual([{}, { refresh: true }]);
    expect(screen.getByRole("button", { name: "Refresh service health" })).toBeEnabled();
  });

  it("offers the refresh button after a failed request, to try again", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    let fail = true;
    server.use(
      http.post(apiUrl, () => (fail ? new HttpResponse(null, { status: 503 }) : HttpResponse.json(serviceHealth))),
    );
    render(<ServiceHealth sessionContext={appContext.sessionContext} apiUrl={apiUrl} />);
    expect(await screen.findByRole("status")).toHaveTextContent("Service health couldn't be loaded.");

    fail = false;
    fireEvent.click(screen.getByRole("button", { name: "Refresh service health" }));
    expect(await screen.findByRole("list", { name: "Backend services" })).toBeInTheDocument();
  });

  it("shows its own ghost, not an error, when the service health can't be loaded", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    server.use(http.post(apiUrl, () => new HttpResponse(null, { status: 503 })));
    render(<ServiceHealth sessionContext={appContext.sessionContext} apiUrl={apiUrl} />);
    const card = screen.getByRole("region", { name: "Service Health" });

    // a screen reader hears why the card is empty; everyone else sees its ghost, still.
    expect(await screen.findByRole("status")).toHaveTextContent(
      "Service health couldn't be loaded. It will try again shortly.",
    );
    expect(screen.getByTestId("service-health-ghost")).toHaveAttribute("aria-hidden", "true");
    expect(screen.getByTestId("service-health-ghost-header")).toBeInTheDocument();
    expect(within(screen.getByTestId("service-health-ghost")).getAllByRole("listitem", { hidden: true })).toHaveLength(
      4,
    );
    expect(card).toHaveAttribute("aria-busy", "false");
    expect(card).not.toHaveClass("service-health-loading");
    expect(card).not.toHaveTextContent(/503|Failed/);
    expect(screen.queryByRole("list", { name: "Backend services" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Refresh service health" })).toBeEnabled();
  });

  it("shows its ghost, shimmering, while it loads", () => {
    server.use(http.post(apiUrl, () => new Promise<Response>(() => {})));
    render(<ServiceHealth sessionContext={appContext.sessionContext} apiUrl={apiUrl} />);
    const card = screen.getByRole("region", { name: "Service Health" });
    expect(card).toHaveAttribute("aria-busy", "true");
    expect(screen.getByTestId("service-health-ghost")).toBeInTheDocument();
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    // the shimmer is a class on the card; a failed card's ghost is still.
    expect(card).toHaveClass("service-health-loading");
  });

  it("replaces its ghost with the content once it loads", async () => {
    renderWith(serviceHealth);
    expect(await screen.findByRole("list", { name: "Backend services" })).toBeInTheDocument();
    expect(screen.queryByTestId("service-health-ghost")).not.toBeInTheDocument();
    expect(screen.queryByTestId("service-health-ghost-header")).not.toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Service Health" })).toHaveAttribute("aria-busy", "false");
  });
});

import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { appContext } from "@/mocks/fixtures";
import { dashboardErrorHandlers, dashboardHandlers } from "@/mocks/handlers";
import { server } from "@test/server";

import Dashboard from "@/components/Dashboard/Component";

describe("Dashboard", () => {
  it("shows the user's resources, the platform's health, and their activity", async () => {
    server.use(...dashboardHandlers);
    render(<Dashboard appContext={appContext} />);

    expect(await screen.findByRole("link", { name: "2 pending" })).toHaveAttribute("href", "/workbench/");
    expect(await screen.findByText("Backend Service Health")).toBeInTheDocument();
    const health = screen.getByLabelText("Service Health");
    expect(within(within(health).getByText("Kubernetes")).getByLabelText("unhealthy")).toBeInTheDocument();

    const actions = await screen.findByRole("region", { name: "Quick Actions" });
    expect(within(actions).getByRole("link", { name: /Documentation/ })).toHaveAttribute("target", "_blank");

    const activity = screen.getByRole("region", { name: "Recent Activity" });
    expect(await within(activity).findByText("Not found")).toBeInTheDocument();
  });

  it("tracks the getting started steps", async () => {
    server.use(...dashboardHandlers);
    render(<Dashboard appContext={appContext} />);
    const steps = await screen.findByRole("region", { name: "Getting Started" });
    expect(steps).toHaveTextContent("1 of 3 steps done");
    expect(within(steps).getByRole("progressbar")).toHaveValue(1);
  });

  it("alerts the user to a locked budget", async () => {
    server.use(...dashboardHandlers);
    render(<Dashboard appContext={appContext} />);
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Budget daily_token_budget on proxy:openai is locked");
    expect(alert).toHaveTextContent("The daily token budget is exhausted.");
  });

  it("shows each widget's error, and still renders the others", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    server.use(...dashboardErrorHandlers);
    render(<Dashboard appContext={appContext} />);

    expect(await screen.findByText(/Failed to load resources/)).toBeInTheDocument();
    expect(await screen.findByText(/Failed to load recent activity/)).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "What's New" })).toBeInTheDocument();
  });
});

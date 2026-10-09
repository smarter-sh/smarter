import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { appContext, budgets, makeBudgetStatus, sessionContext } from "@/mocks/fixtures";
import { budgetsHandlers } from "@/mocks/handlers";
import { server } from "@test/server";

import BudgetVsActualChart from "./Chart";

vi.mock("recharts", async (importOriginal) => (await import("@test/recharts")).withFixedSize(await importOriginal()));

const apiUrl = appContext.budgetsApiUrl;

function renderChart(url = apiUrl) {
  return render(<BudgetVsActualChart sessionContext={sessionContext} apiUrl={url} />);
}

describe("BudgetVsActualChart", () => {
  it("charts the first budget, with its usage", async () => {
    server.use(...budgetsHandlers);
    renderChart();
    expect(screen.getByText("Loading…")).toBeInTheDocument();
    expect(await screen.findByText("This month: $42.50 of $100.00 (43%)")).toBeInTheDocument();
    expect(await screen.findByText("Apr 2026")).toBeInTheDocument();
  });

  it("switches to another budget, and shows that it is blocked", async () => {
    server.use(...budgetsHandlers);
    const user = userEvent.setup();
    renderChart();
    await user.selectOptions(await screen.findByRole("combobox"), "daily_token_budget|proxy:openai");
    expect(await screen.findByTitle("The daily token budget is exhausted.")).toHaveTextContent("Blocked");
    expect(screen.getByText(/^This day: 100,250 tokens of 100,000 tokens/)).toHaveClass("badge-light-danger");
  });

  it("shows a budget's total, that it ended, and an api url without a trailing slash", async () => {
    const status = makeBudgetStatus({
      absolute_limit: 500,
      absolute_actual: 312.75,
      absolute_percent: null,
      is_expired: true,
      is_locked: true,
    });
    let seriesUrl = "";
    server.use(
      http.post("/dashboard/api/budgets", () => HttpResponse.json([status])),
      http.post("/dashboard/api/budgets/:locator/series/", ({ request }) => {
        seriesUrl = new URL(request.url).pathname;
        return HttpResponse.json([{ status: makeBudgetStatus({ budget: "other" }), series: [] }]);
      }),
    );
    renderChart("/dashboard/api/budgets");
    expect(await screen.findByText("Total: $312.75 of $500.00")).toBeInTheDocument();
    expect(screen.getByText("Ended")).toBeInTheDocument();
    expect(screen.getByText("Blocked")).toHaveAttribute("title", "");
    await vi.waitFor(() => expect(seriesUrl).toBe("/dashboard/api/budgets/llmclient%3Aexample/series/"));
  });

  it("says when no budgets apply", async () => {
    server.use(http.post(apiUrl, () => HttpResponse.json([])));
    renderChart();
    expect(await screen.findByText("No budgets apply to you, or to your resources.")).toBeInTheDocument();
  });

  it("shows the api's error when the budgets fail to load", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    server.use(http.post(apiUrl, () => HttpResponse.json({ error: "Service unavailable" }, { status: 503 })));
    renderChart();
    expect(await screen.findByText("(503) Service unavailable")).toBeInTheDocument();
  });

  it("shows the status when the series fails to load without an error body", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    server.use(
      http.post(apiUrl, () => HttpResponse.json(budgets)),
      http.post(`${apiUrl}:locator/series/`, () => new HttpResponse("oops", { status: 500, statusText: "Oops" })),
    );
    renderChart();
    expect(await screen.findByText("(500) Oops")).toBeInTheDocument();
  });
});

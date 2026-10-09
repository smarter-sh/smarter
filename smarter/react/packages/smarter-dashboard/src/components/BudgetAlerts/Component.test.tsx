import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { appContext, makeBudgetStatus, sessionContext } from "@/mocks/fixtures";
import type { BudgetStatus } from "@/components/BudgetVsActual/types";
import { server } from "@test/server";

import BudgetAlerts from "@/components/BudgetAlerts/Component";

function renderWith(statuses: BudgetStatus[]) {
  server.use(http.post(appContext.budgetsApiUrl, () => HttpResponse.json(statuses)));
  return render(<BudgetAlerts sessionContext={sessionContext} apiUrl={appContext.budgetsApiUrl} />);
}

describe("BudgetAlerts", () => {
  it("warns about a budget that is nearly spent this period", async () => {
    renderWith([makeBudgetStatus({ periodic_percent: 85, periodic_actual: 85 })]);
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveClass("alert-warning");
    expect(alert).toHaveTextContent(
      "Budget monthly_llm_budget on llmclient:example has spent 85% of its monthly limit ($85.00 of $100.00).",
    );
  });

  it("warns about a budget whose total is the most spent", async () => {
    renderWith([
      makeBudgetStatus({
        unit: "tokens",
        period: "day",
        periodic_percent: 10,
        absolute_limit: 1000,
        absolute_actual: 1000,
        absolute_percent: 100,
      }),
    ]);
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveClass("alert-danger");
    expect(alert).toHaveTextContent("has spent 100% of its total limit (1,000 tokens of 1,000 tokens).");
  });

  it("says why a budget is locked", async () => {
    renderWith([
      makeBudgetStatus({ budget: "a", is_locked: true, lock_reason: "Exhausted." }),
      makeBudgetStatus({ budget: "b", is_locked: true, periodic_percent: null }),
    ]);
    const alerts = await screen.findAllByRole("alert");
    expect(alerts[0]).toHaveTextContent("is locked: Exhausted.");
    expect(alerts[1]).toHaveTextContent("is locked.");
    expect(alerts[1]).toHaveClass("alert-danger");
  });

  it("ignores budgets that are fine, inactive, expired or without percents", async () => {
    const { container } = renderWith([
      makeBudgetStatus({ budget: "fine" }),
      makeBudgetStatus({ budget: "inactive", is_active: false, is_locked: true }),
      makeBudgetStatus({ budget: "expired", is_expired: true, periodic_percent: 99 }),
      makeBudgetStatus({ budget: "unmeasured", periodic_percent: null, absolute_percent: null }),
    ]);
    // the alerts render only after the api answers: wait for it, then check that there are none.
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(container).toBeEmptyDOMElement();
  });

  it("shows nothing without budgets", async () => {
    const { container } = renderWith([]);
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(container).toBeEmptyDOMElement();
  });
});

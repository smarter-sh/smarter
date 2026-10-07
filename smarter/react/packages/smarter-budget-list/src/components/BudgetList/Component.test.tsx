import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { budgets, listResponse, sessionContext } from "@/mocks/fixtures";
import { listErrorHandlers, listHandlers } from "@/mocks/handlers";
import { server } from "@test/server";

import BudgetList from "./Component";

describe("BudgetList", () => {
  it("lists the budgets, with their limits and blocked resources", async () => {
    server.use(...listHandlers());
    render(<BudgetList sessionContext={sessionContext} />);

    const row = await screen.findByRole("row", { name: /daily_token_budget/ });
    expect(within(row).getByRole("link", { name: "daily_token_budget" })).toHaveAttribute(
      "href",
      budgets[1].manifestUrl,
    );
    expect(within(row).getByText("100,000 tokens / day")).toBeInTheDocument();
    expect(within(row).getByText("1 blocked")).toBeInTheDocument();
    expect(screen.getByRole("row", { name: /monthly_llm_budget/ })).toHaveTextContent("$100.00 / month");
  });

  it("shows a budget's resources, and why one is blocked", async () => {
    server.use(...listHandlers());
    const user = userEvent.setup();
    render(<BudgetList sessionContext={sessionContext} />);

    const row = await screen.findByRole("row", { name: /daily_token_budget/ });
    await user.click(within(row).getByRole("button", { name: "Show resources" }));
    expect(screen.getByText("Proxy openai")).toBeInTheDocument();
    expect(screen.getByTitle("The daily token budget is exhausted.")).toHaveTextContent("Blocked");
  });

  it("deletes a budget, when a superuser confirms", async () => {
    let deleted = "";
    server.use(
      ...listHandlers(),
      http.post("/budget/react-integration/api/delete/:id/", ({ params }) => {
        deleted = String(params.id);
        return HttpResponse.json({});
      }),
    );
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const user = userEvent.setup();
    render(<BudgetList sessionContext={sessionContext} />);

    const row = await screen.findByRole("row", { name: /monthly_llm_budget/ });
    await user.click(within(row).getByRole("button", { name: "Delete" }));
    await vi.waitFor(() => expect(deleted).toBe(String(budgets[0].id)));
  });

  it("does not delete a budget unless the superuser confirms", async () => {
    server.use(...listHandlers());
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
    const user = userEvent.setup();
    render(<BudgetList sessionContext={sessionContext} />);

    const row = await screen.findByRole("row", { name: /monthly_llm_budget/ });
    // an unhandled delete request would fail the test.
    await user.click(within(row).getByRole("button", { name: "Delete" }));
    expect(confirm).toHaveBeenCalledOnce();
  });

  it("does not let a user who is not a superuser delete budgets", async () => {
    server.use(...listHandlers({ ...listResponse, isSuperuser: false }));
    render(<BudgetList sessionContext={sessionContext} />);
    await screen.findByRole("row", { name: /monthly_llm_budget/ });
    expect(screen.queryByRole("button", { name: "Delete" })).not.toBeInTheDocument();
  });

  it("explains that there are no budgets", async () => {
    server.use(...listHandlers({ ...listResponse, isSuperuser: false, objects: [] }));
    render(<BudgetList sessionContext={sessionContext} />);
    expect(await screen.findByText("No budgets apply to you, or to your resources.")).toBeInTheDocument();
  });

  it("shows an error when the budgets cannot be loaded", async () => {
    server.use(...listErrorHandlers);
    render(<BudgetList sessionContext={sessionContext} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Failed to load budgets (500).");
  });
});

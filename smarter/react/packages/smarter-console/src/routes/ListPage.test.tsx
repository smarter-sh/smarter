/** The resource lists that have moved into the console, at their pages' paths. */
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter } from "react-router";
import { beforeEach, describe, expect, it } from "vitest";

import { dashboardHandlers } from "@smarter/dashboard/mocks";
import { listHandlers } from "@smarter/guardrail-list/mocks";

import { server } from "@test/server";

import App from "@/App";
import { LIST_PAGES } from "@/lib/lists";
import { CONSOLE_PAGE_PATHS } from "@/lib/sidebar";
import { userSessionHandler } from "@/mocks/handlers";
import { routes } from "@/router";

function mountAt(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  render(<App router={router} />);
  return router;
}

beforeEach(() => {
  server.use(userSessionHandler, ...dashboardHandlers);
});

describe("the Guardrails list", () => {
  it("lists the user's guardrails from the list api, in the console's frame", async () => {
    server.use(...listHandlers());
    mountAt("/guardrail");
    // the guardrail package's example: the first of the user's own guardrails.
    expect(await screen.findByRole("row", { name: /first_example/ })).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Main" })).toBeInTheDocument();
  });

  it("opens from the sidebar in place, and marks its item", async () => {
    server.use(...listHandlers());
    const router = mountAt("/dashboard");
    const sidebar = within(await screen.findByRole("navigation", { name: "Main" }));
    const link = sidebar.getByRole("link", { name: "Guardrails" });
    expect(link).toHaveAttribute("href", "/guardrail");
    await userEvent.setup().click(link);
    expect(await screen.findByRole("row", { name: /first_example/ })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/guardrail");
    expect(sidebar.getByRole("link", { name: "Guardrails" })).toHaveAttribute("aria-current", "page");
  });
});

describe("the list pages", () => {
  it("each have an api under /api/web/, and open in place", () => {
    for (const page of LIST_PAGES) {
      expect(page.apiUrl).toMatch(/^\/api\/web\/.+\/listview\/$/);
      expect(page.path).not.toMatch(/\/$/);
      expect(CONSOLE_PAGE_PATHS).toContain(page.path);
    }
  });
});

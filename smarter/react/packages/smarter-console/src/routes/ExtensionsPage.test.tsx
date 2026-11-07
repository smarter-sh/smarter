/** The Extensions console, /extensions and /extensions/<slug>, in the console's frame. */
import { render, screen, within } from "@testing-library/react";
import { createMemoryRouter } from "react-router";
import { beforeEach, describe, expect, it } from "vitest";

import { dashboardHandlers } from "@smarter/dashboard/mocks";
import { detailHandlers, listHandlers } from "@smarter/extension-console/mocks";

import { server } from "@test/server";

import App from "@/App";
import { userSession } from "@/mocks/fixtures";
import { sessionHandler, userSessionHandler } from "@/mocks/handlers";
import { routes } from "@/router";

function mountAt(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  render(<App router={router} />);
  return router;
}

const superuserSession = { ...userSession, user: { ...userSession.user!, isSuperuser: true } };

beforeEach(() => {
  server.use(...dashboardHandlers);
});

describe("the Extensions console", () => {
  it("lets a superuser manage the extensions", async () => {
    server.use(sessionHandler(superuserSession), ...listHandlers());
    mountAt("/extensions");
    await screen.findByRole("row", { name: /Weather/ });
    expect(screen.getByLabelText("Enable Weather")).toBeEnabled();
  });

  it("is read-only for a user who is not a superuser", async () => {
    server.use(userSessionHandler, ...listHandlers());
    mountAt("/extensions");
    await screen.findByRole("row", { name: /Weather/ });
    expect(screen.getByLabelText("Enable Weather")).toBeDisabled();
  });

  it("shows an extension's page at its slug, and the sidebar marks Extensions", async () => {
    server.use(sessionHandler(superuserSession), ...detailHandlers());
    mountAt("/extensions/weather/");
    expect(await screen.findByRole("heading", { level: 1, name: "Weather" })).toBeInTheDocument();
    const sidebar = within(screen.getByRole("navigation", { name: "Main" }));
    expect(sidebar.getByRole("link", { name: "Extensions" })).toHaveAttribute("aria-current", "page");
  });
});

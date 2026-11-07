/** The signed-in frame: the sidebar's links, its active item and badge, the drawer, and the theme's layout. */
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { dashboardHandlers } from "@smarter/dashboard/mocks";

import { server } from "@test/server";

import App from "@/App";
import type { ConsoleSession } from "@/contract.gen";
import { activeSidebarItem, CHANGELOG_URL } from "@/lib/sidebar";
import { APP_BODY_CLASS, APP_LAYOUT_ATTRIBUTES, belowLgQuery } from "@/lib/theme";
import { userMenuContext } from "@/lib/userMenu";
import { userSession, userSidebar } from "@/mocks/fixtures";
import { sessionHandler } from "@/mocks/handlers";
import { routes } from "@/router";

// a signed-in user lands on the dashboard, whose widgets call the dashboard api.
beforeEach(() => {
  server.use(...dashboardHandlers);
});

function mountAt(path: string, session: ConsoleSession = userSession) {
  server.use(sessionHandler(session));
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  render(<App router={router} />);
  return router;
}

/** The sidebar's links, once the session has arrived. */
function findSidebar() {
  return screen.findByRole("navigation", { name: "Main" });
}

/** Pretend the window is narrower than the theme's lg breakpoint. */
function narrowWindow() {
  vi.stubGlobal(
    "matchMedia",
    vi.fn(() => ({ matches: true, addEventListener: vi.fn(), removeEventListener: vi.fn() })),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("the sidebar", () => {
  it("links to the session's pages, and leaves out the ones it doesn't have", async () => {
    mountAt("/");
    const nav = await findSidebar();
    expect(within(nav).getByRole("link", { name: "Dashboard" })).toHaveAttribute("href", "/dashboard");
    expect(within(nav).getByRole("link", { name: "Budgets" })).toHaveAttribute("href", "/budget/");
    for (const name of ["Terminal", "Proxies", "Vectorstores", "Infrastructure Resources", "Django Admin"]) {
      expect(within(nav).queryByRole("link", { name })).not.toBeInTheDocument();
    }
    expect(within(nav).queryByText("Settings")).not.toBeInTheDocument();
    expect(within(nav).getByText("Governance")).toBeInTheDocument();
  });

  it("shows a superuser's items, and the extensions with an update", async () => {
    const sidebarLinks = {
      ...userSidebar,
      terminal: "/dashboard/terminal/",
      infrastructureResources: "/infra/",
      admin: "/admin/",
    };
    mountAt("/", { ...userSession, sidebar: sidebarLinks, badges: { extensionUpdates: 2 } });
    const nav = await findSidebar();
    expect(within(nav).getByRole("link", { name: "Terminal" })).toHaveAttribute("href", "/dashboard/terminal/");
    expect(within(nav).getByRole("link", { name: "Django Admin" })).toHaveAttribute("href", "/admin/");
    expect(within(nav).getByText("Settings")).toBeInTheDocument();
    expect(within(nav).getByTitle("Updates available")).toHaveTextContent("2");
  });

  it("opens the documentation in a new tab, and names the version in the change log's link", async () => {
    mountAt("/");
    const nav = await findSidebar();
    const changelog = within(nav).getByRole("link", { name: `GitHub Change Log ${userSession.version}` });
    expect(changelog).toHaveAttribute("href", CHANGELOG_URL);
    expect(changelog).toHaveAttribute("target", "_blank");
    expect(within(nav).getByRole("link", { name: "Read the Docs" })).toHaveAttribute(
      "href",
      userSession.branding.projectDocsUrl,
    );
  });

  it("marks the item of the page", async () => {
    mountAt("/secret/secrets/rMTAwx/");
    const nav = await findSidebar();
    expect(within(nav).getByRole("link", { name: "Secrets" })).toHaveAttribute("aria-current", "page");
    expect(within(nav).getByRole("link", { name: "Dashboard" })).not.toHaveAttribute("aria-current");
  });

  it("finds the item whose url is the longest that begins the path", () => {
    expect(activeSidebarItem("/llm-tools/extensions/weather/", userSidebar)).toBe("extensions");
    expect(activeSidebarItem("/llm-tools/", userSidebar)).toBe("plugins");
    expect(activeSidebarItem("/", userSidebar)).toBeNull();
    // a console route has no trailing slash.
    expect(activeSidebarItem("/dashboard", userSidebar)).toBe("dashboard");
  });
});

describe("the theme's layout", () => {
  it("turns on the theme's app layout while the frame is shown", async () => {
    mountAt("/");
    await findSidebar();
    expect(document.body).toHaveClass(APP_BODY_CLASS);
    for (const [name, value] of Object.entries(APP_LAYOUT_ATTRIBUTES)) {
      expect(document.body).toHaveAttribute(name, value);
    }
  });

  it("reads the lg breakpoint from the theme", () => {
    document.documentElement.style.setProperty("--bs-breakpoint-lg", "1200px");
    expect(belowLgQuery()).toBe("(max-width: calc(1200px - 0.02px))");
    document.documentElement.style.removeProperty("--bs-breakpoint-lg");
    expect(belowLgQuery()).toBe("(max-width: calc(992px - 0.02px))");
  });

  it("is a drawer below the lg breakpoint, which the header opens, and Escape and the overlay close", async () => {
    narrowWindow();
    mountAt("/");
    const user = userEvent.setup();
    const aside = await screen.findByRole("complementary", { hidden: true });
    expect(aside).toHaveClass("drawer", "drawer-start");
    expect(aside).not.toHaveClass("drawer-on");

    await user.click(screen.getByRole("button", { name: "Show the sidebar" }));
    expect(aside).toHaveClass("drawer-on");
    await user.keyboard("{Escape}");
    expect(aside).not.toHaveClass("drawer-on");

    await user.click(screen.getByRole("button", { name: "Show the sidebar" }));
    await user.click(screen.getByRole("button", { name: "Hide the sidebar" }));
    expect(aside).not.toHaveClass("drawer-on");
  });
});

describe("the user menu's context", () => {
  it("comes from the session", () => {
    const context = userMenuContext(userSession, "/secret/");
    expect(context.isAuthenticated).toBe(true);
    expect(context.user.email).toBe(userSession.user!.email);
    expect(context.accountName).toBe(userSession.account!.name);
    expect(context.urls.next).toBe("/secret/");
    expect(context.urls.logout).toBe("/api/web/account/logout/");
    expect(context.sessionContext.csrfCookieName).toBe(userSession.cookies.csrfCookieName);
    expect(context.sessionContext.smarterRequestId).toMatch(/^[0-9a-f]{32}$/);
  });

  it("is empty for a visitor's session", () => {
    const context = userMenuContext({ ...userSession, isAuthenticated: false, user: null, account: null }, "/");
    expect(context.user.username).toBe("");
    expect(context.accountName).toBe("");
    expect(context.userProfileCount).toBe(0);
  });
});

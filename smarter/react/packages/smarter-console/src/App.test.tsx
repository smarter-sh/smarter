/** The console's start: loading its session, then routing a visitor and a signed-in user. */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter } from "react-router";
import { describe, expect, it, vi } from "vitest";

import { server } from "@test/server";

import App from "@/App";
import { userSession } from "@/mocks/fixtures";
import { sessionErrorHandler, sessionHandler, userSessionHandler, visitorSessionHandler } from "@/mocks/handlers";
import { useConsoleSession } from "@/session/context";
import { routes } from "@/router";
import { nextRoute } from "@/lib/next";

function mountAt(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  render(<App router={router} />);
  return router;
}

describe("the console", () => {
  it("shows that it is loading until the session arrives", async () => {
    server.use(userSessionHandler);
    mountAt("/");
    expect(screen.getByRole("status")).toHaveTextContent("Loading...");
    expect(await screen.findByRole("heading", { name: "Welcome, Ada" })).toBeInTheDocument();
  });

  it("shows a signed-in user their account", async () => {
    server.use(userSessionHandler);
    mountAt("/");
    expect(await screen.findByText("ada@example.com")).toBeInTheDocument();
    expect(screen.getByLabelText("Account")).toHaveTextContent("Analytical Engines · 3141-5926-5359");
    expect(screen.getByRole("link", { name: "Open the dashboard" })).toHaveAttribute(
      "href",
      "http://localhost:9357/dashboard/",
    );
  });

  it("sends a visitor to sign in, and remembers where they were going", async () => {
    server.use(visitorSessionHandler);
    const router = mountAt("/secret/?tab=shared");
    expect(await screen.findByRole("heading", { name: "Sign In" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/login");
    expect(router.state.location.search).toBe("?next=%2Fsecret%2F%3Ftab%3Dshared");
    expect(screen.getByRole("link", { name: "Sign in to Smarter" })).toHaveAttribute(
      "href",
      "http://localhost:9357/login/",
    );
  });

  it("sends a signed-in user on from the sign-in page", async () => {
    server.use(userSessionHandler);
    const router = mountAt("/login?next=/unknown/");
    expect(await screen.findByRole("heading", { name: "Page not found" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/unknown/");
  });

  it("offers to try again when the session can't be loaded", async () => {
    server.use(sessionErrorHandler);
    mountAt("/");
    expect(await screen.findByRole("alert")).toHaveTextContent("The console couldn't reach the server.");
    server.use(userSessionHandler);
    await userEvent.setup().click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByRole("heading", { name: "Welcome, Ada" })).toBeInTheDocument();
  });

  it("sets the page's language from the session", async () => {
    server.use(userSessionHandler);
    mountAt("/");
    await screen.findByRole("heading", { name: "Welcome, Ada" });
    expect(document.documentElement.lang).toBe("en");
    expect(document.documentElement.dir).toBe("ltr");
  });
});

describe("the console's fallbacks", () => {
  it("greets a user without a first name by username, and shows no account without a profile", async () => {
    const user = { ...userSession.user!, firstName: "" };
    server.use(sessionHandler({ ...userSession, user, account: null }));
    mountAt("/");
    expect(await screen.findByRole("heading", { name: "Welcome, ada" })).toBeInTheDocument();
    expect(screen.queryByLabelText("Account")).not.toBeInTheDocument();
  });

  it("shows the username of a user without an email", async () => {
    const user = { ...userSession.user!, email: "" };
    server.use(sessionHandler({ ...userSession, user }));
    mountAt("/");
    expect(await screen.findByText("ada", { selector: "div" })).toBeInTheDocument();
  });

  it("writes a right-to-left language right to left", async () => {
    const language = { ...userSession.language, current: "ar", bidi: true };
    server.use(sessionHandler({ ...userSession, language }));
    mountAt("/");
    await screen.findByRole("heading", { name: "Welcome, Ada" });
    expect(document.documentElement.dir).toBe("rtl");
  });

  it("refuses to read the session outside its provider", () => {
    function Orphan() {
      useConsoleSession();
      return null;
    }
    // React logs the error that the test expects.
    vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() => render(<Orphan />)).toThrow("useConsoleSession() must be called inside a SessionProvider.");
  });
});

describe("nextRoute()", () => {
  it("returns a path of this console", () => {
    expect(nextRoute(new URLSearchParams("next=/secret/"))).toBe("/secret/");
  });

  it("never returns another site", () => {
    expect(nextRoute(new URLSearchParams("next=//evil.example/"))).toBe("/");
    expect(nextRoute(new URLSearchParams("next=https://evil.example/"))).toBe("/");
    expect(nextRoute(new URLSearchParams(""))).toBe("/");
  });
});

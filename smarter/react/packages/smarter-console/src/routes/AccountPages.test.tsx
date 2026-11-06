/** The sign-in, sign-up, sign-out and password reset pages, driven through the console's router. */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { createMemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";

import { server } from "@test/server";

import App from "@/App";
import { accountUrls } from "@/lib/account";
import { userSession, visitorSession } from "@/mocks/fixtures";
import {
  accountErrorsHandler,
  accountSessionHandler,
  sessionHandler,
  userSessionHandler,
  visitorSessionHandler,
} from "@/mocks/handlers";
import { routes } from "@/router";

function mountAt(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  render(<App router={router} />);
  return router;
}

describe("the sign-in page", () => {
  it("signs in, and goes on to the page that was asked for", async () => {
    let body: unknown = null;
    server.use(
      visitorSessionHandler,
      http.post(accountUrls.signIn, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json(userSession);
      }),
    );
    const router = mountAt("/login?next=/no-such-page/");
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText("Email"), "ada@example.com");
    await user.type(screen.getByLabelText("Password"), "Correct-Horse-Battery-9");
    await user.click(screen.getByRole("button", { name: "Sign In" }));
    expect(await screen.findByRole("heading", { name: "Page not found" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/no-such-page/");
    expect(body).toEqual({ email: "ada@example.com", password: "Correct-Horse-Battery-9" });
  });

  it("shows why signing in failed", async () => {
    server.use(visitorSessionHandler, accountErrorsHandler(accountUrls.signIn, "Email and/or password do not match."));
    mountAt("/login");
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText("Email"), "ada@example.com");
    await user.type(screen.getByLabelText("Password"), "wrong");
    await user.click(screen.getByRole("button", { name: "Sign In" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Email and/or password do not match.");
    expect(screen.getByRole("button", { name: "Sign In" })).toBeEnabled();
  });

  it("explains an expired session, and a failure that the api didn't explain", async () => {
    server.use(
      visitorSessionHandler,
      http.post(accountUrls.signIn, () => HttpResponse.text("CSRF", { status: 403 })),
    );
    mountAt("/login");
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Sign In" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Your session has expired.");
    server.use(http.post(accountUrls.signIn, () => HttpResponse.text("boom", { status: 502 })));
    await user.click(screen.getByRole("button", { name: "Sign In" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("An unknown error occurred.");
  });

  it("offers Google and GitHub, and sign-up, only when the platform does", async () => {
    server.use(visitorSessionHandler);
    mountAt("/login?next=/secret/");
    expect(await screen.findByRole("link", { name: "Sign in with Google" })).toHaveAttribute(
      "href",
      "/social-auth/login/google-oauth2/?next=%2Fsecret%2F",
    );
    expect(screen.queryByRole("link", { name: "Sign in with GitHub" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sign up" })).toHaveAttribute("href", "/register");
  });

  it("hides sign-up and the OAuth buttons when they are off", async () => {
    const signIn = { ...visitorSession.signIn, google: false, github: true, signUp: false };
    server.use(sessionHandler({ ...visitorSession, signIn }));
    mountAt("/login");
    expect(await screen.findByRole("link", { name: "Sign in with GitHub" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Sign in with Google" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Sign up" })).not.toBeInTheDocument();
  });
});

describe("signing out", () => {
  it("returns to the sign-in page", async () => {
    server.use(userSessionHandler, accountSessionHandler(accountUrls.signOut, visitorSession));
    const router = mountAt("/");
    await userEvent.setup().click(await screen.findByRole("button", { name: "Sign Out" }));
    expect(await screen.findByRole("heading", { name: "Sign In" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/login");
  });

  it("stays signed in when signing out fails", async () => {
    server.use(
      userSessionHandler,
      http.post(accountUrls.signOut, () => HttpResponse.error()),
    );
    mountAt("/");
    await userEvent.setup().click(await screen.findByRole("button", { name: "Sign Out" }));
    expect(await screen.findByRole("button", { name: "Sign Out" })).toBeEnabled();
  });
});

describe("the sign-up page", () => {
  it("signs up, and goes home", async () => {
    server.use(visitorSessionHandler, accountSessionHandler(accountUrls.signUp, userSession));
    mountAt("/register");
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText("Email"), "ada@example.com");
    await user.type(screen.getByLabelText("Password"), "Correct-Horse-Battery-9");
    await user.click(screen.getByRole("button", { name: "Sign Up" }));
    expect(await screen.findByRole("heading", { name: "Welcome, Ada" })).toBeInTheDocument();
  });

  it("shows each field's errors beside it", async () => {
    server.use(
      visitorSessionHandler,
      accountErrorsHandler(accountUrls.signUp, "Please correct the errors below.", {
        email: ["An account with this email address already exists. Please sign in."],
        password: ["This password is too short."],
      }),
    );
    mountAt("/register");
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Sign Up" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Please correct the errors below.");
    expect(screen.getByLabelText("Email")).toHaveAccessibleDescription(
      "An account with this email address already exists. Please sign in.",
    );
    expect(screen.getByLabelText("Password")).toHaveAttribute("aria-invalid", "true");
  });

  it("says so while registration is closed", async () => {
    server.use(sessionHandler({ ...visitorSession, signIn: { ...visitorSession.signIn, signUp: false } }));
    mountAt("/register");
    expect(await screen.findByText("Registration is closed.")).toBeInTheDocument();
    expect(screen.queryByLabelText("Email")).not.toBeInTheDocument();
  });

  it("sends a signed-in user home", async () => {
    server.use(userSessionHandler);
    mountAt("/register");
    expect(await screen.findByRole("heading", { name: "Welcome, Ada" })).toBeInTheDocument();
  });
});

describe("resetting a password", () => {
  const linkPath = "/password-reset-link/MTk1NA/token-1/";
  const apiUrl = accountUrls.passwordReset("MTk1NA", "token-1");

  it("emails a link, and says so", async () => {
    server.use(
      visitorSessionHandler,
      http.post(accountUrls.passwordResetRequest, () =>
        HttpResponse.json({ detail: "If an account has this email address, we have sent it a link." }),
      ),
    );
    mountAt("/password-reset-request");
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText("Email"), "ada@example.com");
    await user.click(screen.getByRole("button", { name: "Send the link" }));
    expect(await screen.findByRole("status")).toHaveTextContent("we have sent it a link");
  });

  it("shows an invalid address's error", async () => {
    server.use(
      visitorSessionHandler,
      accountErrorsHandler(accountUrls.passwordResetRequest, "Please correct the errors below.", {
        email: ["Enter a valid email address."],
      }),
    );
    mountAt("/password-reset-request");
    await userEvent.setup().click(await screen.findByRole("button", { name: "Send the link" }));
    expect(await screen.findByText("Enter a valid email address.")).toBeInTheDocument();
  });

  it("sets the new password from the emailed link", async () => {
    server.use(
      visitorSessionHandler,
      http.get(apiUrl, () => HttpResponse.json({ detail: "Choose a new password." })),
      http.post(apiUrl, () => HttpResponse.json({ detail: "Your password has been changed. Sign in with it." })),
    );
    mountAt(linkPath);
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText("New password"), "Another-Strong-Passw0rd");
    await user.type(screen.getByLabelText("Confirm the new password"), "Another-Strong-Passw0rd");
    await user.click(screen.getByRole("button", { name: "Set the new password" }));
    expect(await screen.findByRole("status")).toHaveTextContent("Your password has been changed.");
  });

  it("shows the new password's errors", async () => {
    server.use(
      visitorSessionHandler,
      http.get(apiUrl, () => HttpResponse.json({ detail: "Choose a new password." })),
      accountErrorsHandler(apiUrl, "Please correct the errors below.", {
        passwordConfirm: ["Passwords do not match."],
      }),
    );
    mountAt(linkPath);
    await userEvent.setup().click(await screen.findByRole("button", { name: "Set the new password" }));
    expect(await screen.findByText("Passwords do not match.")).toBeInTheDocument();
  });

  it("explains a link that can't be used, and offers a new one", async () => {
    server.use(
      visitorSessionHandler,
      http.get(apiUrl, () => HttpResponse.json({ detail: "The link has expired.", fieldErrors: {} }, { status: 403 })),
    );
    mountAt(linkPath);
    expect(await screen.findByRole("alert")).toHaveTextContent("The link has expired.");
    expect(screen.getByRole("link", { name: "Send a new link" })).toHaveAttribute("href", "/password-reset-request");
  });
});

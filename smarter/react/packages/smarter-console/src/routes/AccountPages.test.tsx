/** The sign-in, sign-up, activation, sign-out and password reset pages, driven through the console's router. */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { createMemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { dashboardHandlers } from "@smarter/dashboard/mocks";

import { server } from "@test/server";

import App from "@/App";
import { accountUrls } from "@/lib/account";
import { SESSION_API_URL } from "@/lib/const";
import { userSession, visitorSession } from "@/mocks/fixtures";
import {
  accountErrorsHandler,
  doodleHandler,
  sessionHandler,
  userSessionHandler,
  visitorSessionHandler,
} from "@/mocks/handlers";
import { routes } from "@/router";

// a signed-in user lands on the dashboard, whose widgets call the dashboard api.
beforeEach(() => {
  server.use(...dashboardHandlers);
});

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

  it("offers a new activation link for an account that isn't activated yet", async () => {
    server.use(
      visitorSessionHandler,
      accountErrorsHandler(accountUrls.signIn, "Your account isn't activated yet.", {}, 403),
    );
    mountAt("/login");
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText("Email"), "ada@example.com");
    await user.type(screen.getByLabelText("Password"), "Correct-Horse-Battery-9");
    await user.click(screen.getByRole("button", { name: "Sign In" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Your account isn't activated yet.");
    expect(screen.getByRole("link", { name: "Send a new activation link" })).toHaveAttribute(
      "href",
      "/account/inactive",
    );
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

describe("the sign-in pages' frame", () => {
  it("shows the doodle of the day while its switch is on", async () => {
    const signIn = { ...visitorSession.signIn, doodle: true };
    server.use(sessionHandler({ ...visitorSession, signIn }), doodleHandler);
    mountAt("/login");
    expect(await screen.findByRole("link", { name: "Happy Diwali!" })).toHaveAttribute(
      "href",
      "https://en.wikipedia.org/wiki/Diwali",
    );
  });

  it("shows the logo, name and description without the doodle", async () => {
    server.use(visitorSessionHandler);
    mountAt("/login");
    expect(await screen.findByText(visitorSession.branding.productName)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Learn more" })).toHaveAttribute(
      "href",
      visitorSession.branding.projectWebsiteUrl,
    );
  });

  it("shows the footer's links only while they are switched on", async () => {
    server.use(visitorSessionHandler);
    mountAt("/login");
    await screen.findByLabelText("Email");
    expect(screen.queryByRole("navigation", { name: "Legal" })).not.toBeInTheDocument();
  });

  it("links to the legal page, the plans and the contact page", async () => {
    const signIn = { ...visitorSession.signIn, footerLinks: true };
    server.use(sessionHandler({ ...visitorSession, signIn }));
    mountAt("/login");
    expect(await screen.findByRole("link", { name: "Legal" })).toHaveAttribute(
      "href",
      visitorSession.branding.legalUrl,
    );
    expect(screen.getByRole("link", { name: "Contact Us" })).toHaveAttribute(
      "href",
      visitorSession.branding.contactUrl,
    );
  });
});

describe("signing out", () => {
  it("signs out from the user menu, and returns to the sign-in page", async () => {
    let signedOut = false;
    server.use(
      http.get(SESSION_API_URL, () => HttpResponse.json(signedOut ? visitorSession : userSession)),
      http.post(accountUrls.signOut, () => {
        signedOut = true;
        return HttpResponse.json(visitorSession);
      }),
    );
    const router = mountAt("/");
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "ada@example.com" }));
    await user.click(screen.getByRole("button", { name: "Sign Out" }));
    expect(await screen.findByRole("heading", { name: "Sign In" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/login");
  });

  it("stays signed in, and says why, when signing out fails", async () => {
    server.use(
      userSessionHandler,
      http.post(accountUrls.signOut, () => HttpResponse.json({ detail: "Forbidden" }, { status: 403 })),
    );
    vi.spyOn(console, "error").mockImplementation(() => {});
    mountAt("/");
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "ada@example.com" }));
    await user.click(screen.getByRole("button", { name: "Sign Out" }));
    expect(await screen.findByText("Request failed: 403")).toHaveAttribute("role", "alert");
    expect(screen.getByRole("button", { name: "Sign Out" })).toBeEnabled();
  });
});

describe("the sign-up page", () => {
  it("signs up, and says to check the email for the activation link", async () => {
    server.use(
      visitorSessionHandler,
      http.post(accountUrls.signUp, () =>
        HttpResponse.json({ detail: "We have emailed you a link to activate your account." }),
      ),
    );
    mountAt("/register");
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText("Email"), "ada@example.com");
    await user.type(screen.getByLabelText("Password"), "Correct-Horse-Battery-9");
    await user.click(screen.getByRole("button", { name: "Sign Up" }));
    expect(await screen.findByRole("heading", { name: "Check your email" })).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("We have emailed you a link to activate your account.");
    expect(screen.getByRole("link", { name: "Didn't get the email?" })).toHaveAttribute("href", "/account/inactive");
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
    expect(await screen.findByRole("region", { name: "Dashboard" })).toBeInTheDocument();
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

describe("activating an account", () => {
  const linkPath = "/account/activate/MTk1NA/token-1/";
  const apiUrl = accountUrls.activate("MTk1NA", "token-1");

  it("activates the account once, signs in, and goes home", async () => {
    let posts = 0;
    server.use(
      visitorSessionHandler,
      http.post(apiUrl, () => {
        posts += 1;
        return HttpResponse.json(userSession);
      }),
    );
    const router = mountAt(linkPath);
    expect(await screen.findByRole("region", { name: "Dashboard" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/dashboard");
    expect(posts).toBe(1);
  });

  it("explains a link that can't be used, and offers a new one", async () => {
    server.use(visitorSessionHandler, accountErrorsHandler(apiUrl, "The link has expired.", {}, 403));
    mountAt(linkPath);
    expect(await screen.findByRole("alert")).toHaveTextContent("The link has expired.");
    expect(screen.getByRole("link", { name: "Send a new activation link" })).toHaveAttribute(
      "href",
      "/account/inactive",
    );
  });

  it("sends a signed-in user home", async () => {
    server.use(userSessionHandler);
    mountAt(linkPath);
    expect(await screen.findByRole("region", { name: "Dashboard" })).toBeInTheDocument();
  });
});

describe("the inactive account page", () => {
  it("emails a new activation link, and says so", async () => {
    let body: unknown = null;
    server.use(
      visitorSessionHandler,
      http.post(accountUrls.activationResend, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json({ detail: "If an account with this email address is waiting, we sent a link." });
      }),
    );
    mountAt("/account/inactive/");
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText("Email"), "ada@example.com");
    await user.click(screen.getByRole("button", { name: "Send a new activation link" }));
    expect(await screen.findByRole("status")).toHaveTextContent("we sent a link");
    expect(body).toEqual({ email: "ada@example.com" });
  });

  it("shows an invalid address's error", async () => {
    server.use(
      visitorSessionHandler,
      accountErrorsHandler(accountUrls.activationResend, "Please correct the errors below.", {
        email: ["Enter a valid email address."],
      }),
    );
    mountAt("/account/inactive/");
    await userEvent.setup().click(await screen.findByRole("button", { name: "Send a new activation link" }));
    expect(await screen.findByText("Enter a valid email address.")).toBeInTheDocument();
  });
});

describe("the already associated page", () => {
  it("says that the social account belongs to another user", async () => {
    server.use(visitorSessionHandler);
    mountAt("/account/already-associated/");
    expect(await screen.findByRole("heading", { name: "Social Account Already Associated" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to sign in" })).toHaveAttribute("href", "/login");
  });
});

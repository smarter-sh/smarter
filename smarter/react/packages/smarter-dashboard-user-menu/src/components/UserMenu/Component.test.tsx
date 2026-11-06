import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { anonymousAppContext, appContext, singleProfileAppContext } from "@/mocks/fixtures";
import { signOutErrorHandler, signOutHandler, userProfileHandlers } from "@/mocks/handlers";
import { server } from "@test/server";

import UserMenu from "@/components/UserMenu/Component";

const menuButton = () => screen.getByRole("button", { name: "ada@example.edu" });

describe("UserMenu", () => {
  it("opens and closes from the profile image, and closes on Escape and on a click outside it", async () => {
    const user = userEvent.setup();
    render(
      <>
        <p>outside</p>
        <UserMenu appContext={appContext} />
      </>,
    );
    expect(menuButton()).toHaveAttribute("aria-expanded", "false");
    await user.click(menuButton());
    expect(menuButton()).toHaveAttribute("aria-expanded", "true");
    await user.click(menuButton());
    expect(menuButton()).toHaveAttribute("aria-expanded", "false");

    await user.click(menuButton());
    await user.keyboard("{Escape}");
    expect(menuButton()).toHaveAttribute("aria-expanded", "false");
    expect(menuButton()).toHaveFocus();

    await user.click(menuButton());
    await user.click(screen.getByText("outside"));
    expect(menuButton()).toHaveAttribute("aria-expanded", "false");
  });

  it("shows who the user is, the account, and every item for a user with two profiles", async () => {
    render(<UserMenu appContext={appContext} />);
    expect(screen.getByText("ada")).toBeInTheDocument();
    expect(screen.getByText("Ada Lovelace")).toBeInTheDocument();
    expect(screen.getByText("Introduction to Prompt Engineering")).toBeInTheDocument();
    expect(screen.queryByText("Superuser")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Language/ })).toBeInTheDocument();
    expect(screen.getByText("Change Profile Image")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Remove Profile Image" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Change Profile" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Welcome Tour" })).toHaveAttribute("data-smarter-welcome-open", "true");
    expect(screen.getByRole("button", { name: "Sign Out" })).toBeInTheDocument();
  });

  it("has no Change Profile item, and no account, for a user with one profile", () => {
    render(<UserMenu appContext={singleProfileAppContext} />);
    expect(screen.queryByRole("button", { name: "Change Profile" })).not.toBeInTheDocument();
    expect(screen.queryByText("Introduction to Prompt Engineering")).not.toBeInTheDocument();
  });

  it("shows the Superuser badge, else the Staff badge", () => {
    const { rerender } = render(
      <UserMenu appContext={{ ...appContext, user: { ...appContext.user, isSuperuser: true, isStaff: true } }} />,
    );
    expect(screen.getByText("Superuser")).toBeInTheDocument();
    expect(screen.queryByText("Staff")).not.toBeInTheDocument();
    rerender(<UserMenu appContext={{ ...appContext, user: { ...appContext.user, isStaff: true } }} />);
    expect(screen.getByText("Staff")).toBeInTheDocument();
  });

  it("offers only Sign In and the languages to an anonymous request", () => {
    render(<UserMenu appContext={anonymousAppContext} />);
    expect(screen.getByRole("link", { name: "Sign In" })).toHaveAttribute("href", "/login/");
    expect(screen.getByRole("button", { name: /Language/ })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Sign Out" })).not.toBeInTheDocument();
    expect(screen.queryByText("Change Profile Image")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Welcome Tour" })).not.toBeInTheDocument();
  });

  it("closes the menu when Welcome Tour is chosen", async () => {
    const user = userEvent.setup();
    render(<UserMenu appContext={appContext} />);
    await user.click(menuButton());
    await user.click(screen.getByRole("button", { name: "Welcome Tour" }));
    expect(menuButton()).toHaveAttribute("aria-expanded", "false");
  });

  it("signs out with the account api, then goes to the sign-in page", async () => {
    const user = userEvent.setup();
    server.use(signOutHandler);
    const onSignedOut = vi.fn();
    render(<UserMenu appContext={appContext} onSignedOut={onSignedOut} />);
    await user.click(menuButton());
    await user.click(screen.getByRole("button", { name: "Sign Out" }));
    await waitFor(() => expect(onSignedOut).toHaveBeenCalledWith("/login/"));
  });

  it("stays, and says why, when signing out fails", async () => {
    const user = userEvent.setup();
    server.use(signOutErrorHandler);
    const onSignedOut = vi.fn();
    vi.spyOn(console, "error").mockImplementation(() => {});
    render(<UserMenu appContext={appContext} onSignedOut={onSignedOut} />);
    await user.click(menuButton());
    await user.click(screen.getByRole("button", { name: "Sign Out" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Request failed: 403");
    expect(screen.getByRole("button", { name: "Sign Out" })).toBeEnabled();
    expect(onSignedOut).not.toHaveBeenCalled();
  });

  it("opens the Change Profile dialog, closes the menu, and returns the focus when the dialog closes", async () => {
    const user = userEvent.setup();
    server.use(...userProfileHandlers);
    const onSwitched = vi.fn();
    render(<UserMenu appContext={appContext} onSwitched={onSwitched} />);
    await user.click(menuButton());
    await user.click(screen.getByRole("button", { name: "Change Profile" }));
    expect(menuButton()).toHaveAttribute("aria-expanded", "false");
    expect(await screen.findByRole("dialog", { name: "Change Profile" })).toBeInTheDocument();
    await user.click(screen.getAllByRole("button", { name: "Close" })[0]);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(menuButton()).toHaveFocus();
    expect(onSwitched).not.toHaveBeenCalled();
  });
});

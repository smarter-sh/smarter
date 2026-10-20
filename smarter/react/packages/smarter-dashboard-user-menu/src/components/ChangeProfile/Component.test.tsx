import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { appContext, sessionContext, switchedUserProfiles, userProfiles } from "@/mocks/fixtures";
import { userProfileHandlers, userProfilesErrorHandlers } from "@/mocks/handlers";
import { server } from "@test/server";

import ChangeProfile from "@/components/ChangeProfile/Component";

function renderDialog(onSwitched = vi.fn(), onClose = vi.fn()) {
  render(
    <ChangeProfile
      sessionContext={sessionContext}
      userProfilesApiUrl={appContext.urls.userProfilesApi}
      userProfileSelectApiUrl={appContext.urls.userProfileSelectApi}
      onClose={onClose}
      onSwitched={onSwitched}
    />,
  );
  return { onSwitched, onClose };
}

describe("ChangeProfile", () => {
  it("lists the user's profiles with their account number, account name and creation date", async () => {
    server.use(...userProfileHandlers);
    renderDialog();
    expect(screen.getByRole("status")).toHaveTextContent("Loading…");
    const rows = await screen.findAllByRole("row");
    expect(
      within(rows[0])
        .getAllByRole("columnheader")
        .map((header) => header.textContent),
    ).toEqual(["Account Number", "Account Name", "Profile Created", "Switch"]);
    expect(within(rows[1]).getByText("1234-5678-9012")).toBeInTheDocument();
    expect(within(rows[1]).getByText("Introduction to Prompt Engineering")).toBeInTheDocument();
    expect(
      within(rows[1]).getByText(
        new Date("2026-09-01T14:03:00Z").toLocaleDateString(undefined, {
          year: "numeric",
          month: "2-digit",
          day: "2-digit",
        }),
      ),
    ).toBeInTheDocument();
    expect(rows[1]).toHaveAttribute("aria-current", "true");
    expect(within(rows[1]).getByText("Current")).toBeInTheDocument();
    expect(within(rows[2]).getByRole("button", { name: "Switch to Building AI Agents" })).toBeEnabled();
  });

  it("chooses another profile, then calls onSwitched", async () => {
    const user = userEvent.setup();
    const bodies: unknown[] = [];
    server.use(
      http.post(appContext.urls.userProfilesApi, () => HttpResponse.json(userProfiles)),
      http.post(appContext.urls.userProfileSelectApi, async ({ request }) => {
        bodies.push(await request.json());
        return HttpResponse.json(switchedUserProfiles);
      }),
    );
    const { onSwitched } = renderDialog();
    await user.click(await screen.findByRole("button", { name: "Switch to Building AI Agents" }));
    expect(bodies).toEqual([{ userProfileId: 7 }]);
    expect(onSwitched).toHaveBeenCalledTimes(1);
    expect(screen.getAllByRole("row")[2]).toHaveAttribute("aria-current", "true");
  });

  it("shows the select api's error, and lets the user try again", async () => {
    const user = userEvent.setup();
    server.use(
      http.post(appContext.urls.userProfilesApi, () => HttpResponse.json(userProfiles)),
      http.post(appContext.urls.userProfileSelectApi, () =>
        HttpResponse.json({ error: "Not one of your profiles." }, { status: 404 }),
      ),
    );
    const { onSwitched } = renderDialog();
    await user.click(await screen.findByRole("button", { name: "Switch to Building AI Agents" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Not one of your profiles.");
    expect(onSwitched).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Switch to Building AI Agents" })).toBeEnabled();
  });

  it("shows the list api's error, or its status when it has no message", async () => {
    server.use(...userProfilesErrorHandlers);
    renderDialog();
    expect(await screen.findByRole("alert")).toHaveTextContent("Service unavailable");
  });

  it("shows the status of a failed request without a JSON body", async () => {
    server.use(http.post(appContext.urls.userProfilesApi, () => new HttpResponse("oops", { status: 500 })));
    renderDialog();
    expect(await screen.findByRole("alert")).toHaveTextContent("Request failed: 500");
  });

  it("closes on Escape", async () => {
    const user = userEvent.setup();
    server.use(...userProfileHandlers);
    const { onClose } = renderDialog();
    await screen.findAllByRole("row");
    await user.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalled();
  });
});

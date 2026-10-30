import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { extensionObjects, ownedObjects, sessionContext, sharedObjects } from "@/mocks/fixtures";
import { listErrorHandlers, listHandlers } from "@/mocks/handlers";
import { resourceDetailHandler } from "@test/resourceDetail";
import { server } from "@test/server";

import App from "@/App";

describe("App", () => {
  it("lists your own, and those shared with you", async () => {
    server.use(...listHandlers());
    const user = userEvent.setup();
    render(<App sessionContext={sessionContext} />);

    expect(await screen.findByRole("row", { name: new RegExp(ownedObjects[0].name) })).toBeInTheDocument();
    expect(screen.queryByRole("row", { name: new RegExp(sharedObjects[0].name) })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Shared Tool Plugins" }));
    expect(await screen.findByRole("row", { name: new RegExp(sharedObjects[0].name) })).toBeInTheDocument();
  });

  it("lists the extensions available to you, read-only", async () => {
    server.use(...listHandlers());
    const user = userEvent.setup();
    render(<App sessionContext={sessionContext} />);
    await screen.findByRole("row", { name: new RegExp(ownedObjects[0].name) });

    await user.click(screen.getByRole("button", { name: "Extensions" }));
    for (const extension of extensionObjects) {
      expect(await screen.findByRole("row", { name: new RegExp(extension.displayName) })).toBeInTheDocument();
    }
    expect(screen.queryByRole("row", { name: new RegExp(ownedObjects[0].name) })).not.toBeInTheDocument();
    expect(screen.getByRole("searchbox", { name: "Search" })).toHaveAttribute("placeholder", "Search Extensions");
    // read-only: no operations, for any user.
    expect(screen.queryByRole("columnheader", { name: "Operations" })).not.toBeInTheDocument();
    expect(screen.queryByRole("group", { name: "Actions" })).not.toBeInTheDocument();
  });

  it("opens a plugin's detail when its row is chosen", async () => {
    server.use(...listHandlers(), resourceDetailHandler());
    const user = userEvent.setup();
    render(<App sessionContext={sessionContext} />);

    await user.click(await screen.findByText(ownedObjects[0].name));
    const detail = within(await screen.findByRole("dialog", { name: ownedObjects[0].name }));
    expect(detail.getByRole("heading", { name: "Selector" })).toBeInTheDocument();
    await user.click(detail.getByRole("tab", { name: /Dependencies/ }));
    expect(await detail.findByText("stackademy")).toBeInTheDocument();
  });

  it("opens an extension's read-only detail, which has only its Details tab, when its row is chosen", async () => {
    server.use(...listHandlers());
    const user = userEvent.setup();
    render(<App sessionContext={sessionContext} />);
    await screen.findByRole("row", { name: new RegExp(ownedObjects[0].name) });

    await user.click(screen.getByRole("button", { name: "Extensions" }));
    await user.click(await screen.findByText(extensionObjects[0].displayName));
    // an extension has no name: its detail is called by its display name.
    const detail = within(await screen.findByRole("dialog", { name: extensionObjects[0].displayName }));
    expect(detail.getByRole("heading", { name: "Installation" })).toBeInTheDocument();
    expect(detail.getAllByRole("tab").map((tab) => tab.textContent)).toEqual(["Details"]);
    expect(detail.queryByRole("group", { name: "Actions" })).not.toBeInTheDocument();
  });

  it("shows the api's error", async () => {
    server.use(...listErrorHandlers);
    render(<App sessionContext={sessionContext} />);
    expect(await screen.findByText("Database unavailable")).toBeInTheDocument();
  });
});

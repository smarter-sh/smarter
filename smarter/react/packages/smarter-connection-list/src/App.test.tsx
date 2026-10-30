import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { ownedObjects, sessionContext, sharedObjects } from "@/mocks/fixtures";
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

    await user.click(screen.getByRole("button", { name: "Shared Connections" }));
    expect(await screen.findByRole("row", { name: new RegExp(sharedObjects[0].name) })).toBeInTheDocument();
  });

  it("opens a connection's detail when its row is chosen", async () => {
    server.use(...listHandlers(), resourceDetailHandler());
    const user = userEvent.setup();
    render(<App sessionContext={sessionContext} />);

    await user.click(await screen.findByText(ownedObjects[0].name));
    const detail = within(await screen.findByRole("dialog", { name: ownedObjects[0].name }));
    expect(detail.getByRole("heading", { name: "Connection" })).toBeInTheDocument();
    await user.click(detail.getByRole("tab", { name: /Dependencies/ }));
    expect(await detail.findByText("stackademy")).toBeInTheDocument();
  });

  it("shows the api's error", async () => {
    server.use(...listErrorHandlers);
    render(<App sessionContext={sessionContext} />);
    expect(await screen.findByText("Database unavailable")).toBeInTheDocument();
  });
});

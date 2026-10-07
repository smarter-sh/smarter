import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { ownedObjects, sessionContext, sharedObjects } from "@/mocks/fixtures";
import { listErrorHandlers, listHandlers } from "@/mocks/handlers";
import { server } from "@test/server";

import App from "./App";

describe("App", () => {
  it("lists your own, and those shared with you", async () => {
    server.use(...listHandlers());
    const user = userEvent.setup();
    render(<App sessionContext={sessionContext} />);

    expect(await screen.findByRole("row", { name: new RegExp(ownedObjects[0].name) })).toBeInTheDocument();
    expect(screen.queryByRole("row", { name: new RegExp(sharedObjects[0].name) })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Shared LLM Clients" }));
    expect(await screen.findByRole("row", { name: new RegExp(sharedObjects[0].name) })).toBeInTheDocument();
  });

  it("shows cards in the thumbnail view", async () => {
    server.use(...listHandlers());
    const user = userEvent.setup();
    render(<App sessionContext={sessionContext} />);

    await screen.findByRole("row", { name: new RegExp(ownedObjects[0].name) });
    await user.click(screen.getByRole("button", { name: "Thumbnail View" }));
    expect(screen.queryByRole("columnheader", { name: "Operations" })).not.toBeInTheDocument();
    expect(screen.getAllByText(ownedObjects[0].name).length).toBeGreaterThan(0);
  });

  it("shows the api's error", async () => {
    server.use(...listErrorHandlers);
    render(<App sessionContext={sessionContext} />);
    expect(await screen.findByText("Database unavailable")).toBeInTheDocument();
  });
});

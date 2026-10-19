import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import App from "@/App";
import { firstApiKey, publicContext, workbenchContext } from "@/mocks/fixtures";
import { actionHandlers } from "@/mocks/handlers";
import { server } from "@test/server";

describe("App", () => {
  it("renders the page at the deployed LLMClient's url: no owner, no api keys, and The Smarter Project", () => {
    render(<App context={publicContext} />);
    expect(screen.getByRole("heading", { level: 1, name: "Deployed" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to the workbench" })).toHaveAttribute(
      "href",
      publicContext.page.llmclient.workbenchUrl,
    );
    expect(screen.queryByRole("rowheader", { name: "Owner" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Choose its api key" })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Create an api key" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Build your own LLM applications" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "For platform administrators" })).toBeInTheDocument();
    expect(screen.getByRole("contentinfo")).toBeInTheDocument();
    expect(screen.queryByText(/This tab is always here/)).not.toBeInTheDocument();
  });

  it("renders the workbench's tab: the owner, the api keys, and the note about the endpoints page", () => {
    render(<App context={workbenchContext} />);
    expect(screen.queryByRole("link", { name: "Back to the workbench" })).not.toBeInTheDocument();
    expect(screen.getByRole("rowheader", { name: "Owner" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Choose its api key" })).toBeInTheDocument();
    expect(screen.getByText(/This tab is always here/)).toBeInTheDocument();
    expect(screen.queryByRole("contentinfo")).not.toBeInTheDocument();
  });

  it("shows the page as it is after an action", async () => {
    server.use(...actionHandlers());
    const user = userEvent.setup();
    render(<App context={workbenchContext} />);
    expect(screen.getAllByText("Public").length).toBeGreaterThan(0);
    const row = screen.getByRole("row", { name: new RegExp(firstApiKey.name) });
    await user.click(within(row).getByRole("button", { name: "Attach" }));
    expect(await screen.findByText(/my_site_chat is attached/)).toBeInTheDocument();
    // the hero's card, and the commands, are the new page's: the url now requires an api key.
    expect(screen.getByText("Api key required")).toBeInTheDocument();
  });
});

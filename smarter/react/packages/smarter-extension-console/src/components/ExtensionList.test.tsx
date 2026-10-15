import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import ExtensionList from "@/components/ExtensionList";
import { API_URL, disabledRegistry, listContext, listResponse } from "@/mocks/fixtures";
import { errorHandlers, listHandlers } from "@/mocks/handlers";
import { server } from "@test/server";

describe("ExtensionList", () => {
  it("lists the installed extensions, with their versions, badges and errors", async () => {
    server.use(...listHandlers());
    render(<ExtensionList context={listContext} />);
    const row = await screen.findByRole("row", { name: /Weather/ });
    expect(within(row).getByRole("link", { name: "Weather" })).toHaveAttribute("href", "/extensions/weather/");
    expect(within(row).getByText("0.2.0 available")).toBeInTheDocument();
    expect(within(row).getByText("Official Smarter Extension")).toBeInTheDocument();
    expect(screen.getByLabelText("Error")).toHaveAttribute("title", expect.stringContaining("post_install failed"));
    expect(screen.getByLabelText("Enable Acme CRM")).not.toBeChecked();
  });

  it("enables and disables an extension, and reports it", async () => {
    server.use(...listHandlers());
    const user = userEvent.setup();
    render(<ExtensionList context={listContext} />);
    await user.click(await screen.findByLabelText("Enable Weather"));
    expect(await screen.findByText("Disabled.")).toBeInTheDocument();
    await user.click(screen.getByLabelText("Enable Acme CRM"));
    expect(await screen.findByText("Enabled.")).toBeInTheDocument();
  });

  it("checks the registry for updates", async () => {
    server.use(...listHandlers());
    const user = userEvent.setup();
    render(<ExtensionList context={listContext} />);
    await screen.findByRole("row", { name: /Weather/ });
    await user.click(screen.getByRole("button", { name: /Check for updates/ }));
    expect(await screen.findByText("Updates are available: Weather 0.2.0.")).toBeInTheDocument();
  });

  it("browses, filters and installs from the registry", async () => {
    server.use(...listHandlers());
    const navigate = vi.fn();
    const user = userEvent.setup();
    render(<ExtensionList context={listContext} navigate={navigate} />);
    await user.click(screen.getByRole("tab", { name: "Browse the registry" }));

    expect(await screen.findByRole("article", { name: "Weather" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Update to 0.2.0" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Installed (0.1.0)" })).toHaveAttribute("href", "/extensions/calculator/");
    expect(screen.getByText("Not compatible with this version of Smarter")).toBeInTheDocument();

    await user.type(screen.getByLabelText("Search extensions"), "date");
    expect(screen.queryByRole("article", { name: "Weather" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Install 0.1.0" }));
    expect(navigate).toHaveBeenCalledWith("/extensions/date-calculator/");

    await user.clear(screen.getByLabelText("Search extensions"));
    await user.selectOptions(screen.getByLabelText("Publisher"), "community");
    expect(screen.getByRole("article", { name: "Stock Quotes" })).toBeInTheDocument();
    expect(screen.queryByRole("article", { name: "Weather" })).not.toBeInTheDocument();
    await user.type(screen.getByLabelText("Search extensions"), "nothing");
    expect(screen.getByText("No extensions match.")).toBeInTheDocument();
  });

  it("shows a registry extension's details, and installs a chosen version", async () => {
    server.use(...listHandlers());
    const navigate = vi.fn();
    const user = userEvent.setup();
    render(<ExtensionList context={listContext} navigate={navigate} />);
    await user.click(screen.getByRole("tab", { name: "Browse the registry" }));
    const card = await screen.findByRole("article", { name: "Weather" });
    await user.click(within(card).getByRole("button", { name: "Details" }));

    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByText("Current weather, from Open-Meteo.")).toBeInTheDocument();
    await user.selectOptions(within(dialog).getByLabelText("Version"), "0.1.0");
    await user.click(within(dialog).getByRole("button", { name: "Install this version" }));
    expect(navigate).toHaveBeenCalledWith("/extensions/weather/");
  });

  it("uploads an archive, and opens its page", async () => {
    server.use(...listHandlers());
    const navigate = vi.fn();
    const user = userEvent.setup();
    render(<ExtensionList context={listContext} navigate={navigate} />);
    await screen.findByRole("row", { name: /Weather/ });
    await user.upload(screen.getByLabelText("Extension archive"), new File(["zip"], "acme-crm-1.0.0.zip"));
    await vi.waitFor(() => expect(navigate).toHaveBeenCalledWith("/extensions/acme-crm/"));
  });

  it("shows why an upload or an install failed", async () => {
    // the first handler that matches answers, so the failures come before the list's handlers.
    server.use(
      http.post(`${API_URL}upload/`, () =>
        HttpResponse.json({ error: "the archive is not a zip file" }, { status: 400 }),
      ),
      http.post(`${API_URL}install/`, () =>
        HttpResponse.json({ error: "the archive's sha256 is wrong" }, { status: 400 }),
      ),
      ...listHandlers(),
    );
    const user = userEvent.setup();
    render(<ExtensionList context={listContext} />);
    await screen.findByRole("row", { name: /Weather/ });
    await user.upload(screen.getByLabelText("Extension archive"), new File(["x"], "x.zip"));
    expect(await screen.findByText("the archive is not a zip file")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Dismiss" }));
    await user.click(screen.getByRole("tab", { name: "Browse the registry" }));
    await user.click(await screen.findByRole("button", { name: "Update to 0.2.0" }));
    expect(await screen.findByText("the archive's sha256 is wrong")).toBeInTheDocument();
  });

  it("says when nothing is installed, and why the registry can't be browsed", async () => {
    server.use(...listHandlers({ ...listResponse, objects: [], registryEnabled: false }, disabledRegistry));
    const user = userEvent.setup();
    render(<ExtensionList context={listContext} />);
    expect(await screen.findByText(/No extensions are installed/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Check for updates/ })).toBeDisabled();
    await user.click(screen.getByRole("tab", { name: "Browse the registry" }));
    expect(await screen.findByText(/SMARTER_EXTENSION_REGISTRY_PUBLIC_KEY/)).toBeInTheDocument();
  });

  it("shows the api's error", async () => {
    server.use(...errorHandlers);
    const user = userEvent.setup();
    render(<ExtensionList context={listContext} />);
    expect(await screen.findByText("Database unavailable")).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: "Browse the registry" }));
    await user.click(screen.getByRole("tab", { name: "Installed" }));
    expect(screen.getAllByText("Database unavailable").length).toBeGreaterThan(0);
  });
});

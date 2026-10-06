import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { listResponse, makeResource, resources, sessionContext } from "@/mocks/fixtures";
import { listErrorHandlers, listForbiddenHandlers, listHandlers } from "@/mocks/handlers";
import { server } from "@test/server";

import InfrastructureResourceList from "./Component";
import { defaultFilters, filterResources } from "./filters";

describe("InfrastructureResourceList", () => {
  it("summarizes the ledger, and lists the active resources", async () => {
    server.use(...listHandlers());
    render(<InfrastructureResourceList sessionContext={sessionContext} />);

    const summary = await screen.findByLabelText("Summary");
    expect(within(summary).getByLabelText("Active and billable: 2")).toBeInTheDocument();
    const row = screen.getByRole("row", { name: /customer\.example\.com.*dns\.zone.*aws/ });
    expect(within(row).getByText("dns.zone")).toBeInTheDocument();
    expect(within(row).getByText("Billable")).toBeInTheDocument();
    expect(within(row).getByText("Active")).toBeInTheDocument();
    // destroyed resources are not listed by default.
    expect(screen.queryByText("Destroyed", { selector: "span.badge" })).not.toBeInTheDocument();
  });

  it("filters by status, billable, provider and text", async () => {
    server.use(...listHandlers());
    const user = userEvent.setup();
    render(<InfrastructureResourceList sessionContext={sessionContext} />);

    await user.selectOptions(await screen.findByRole("combobox", { name: "Status" }), "destroyed");
    expect(screen.getAllByRole("row")).toHaveLength(2);
    expect(screen.getByText("Destroyed", { selector: "span.badge" })).toBeInTheDocument();

    await user.selectOptions(screen.getByRole("combobox", { name: "Status" }), "all");
    await user.selectOptions(screen.getByRole("combobox", { name: "Provider" }), "memory");
    expect(screen.getAllByRole("row")).toHaveLength(2);
    expect(screen.getByText("local.example.com")).toBeInTheDocument();

    await user.selectOptions(screen.getByRole("combobox", { name: "Provider" }), "");
    await user.type(screen.getByRole("searchbox", { name: "Search" }), "nothing matches this");
    expect(screen.getByText("No resources match the filters.")).toBeInTheDocument();
  });

  it("refreshes the list", async () => {
    let requests = 0;
    server.use(
      http.post(sessionContext.ApiUrl, () => {
        requests += 1;
        return HttpResponse.json(listResponse);
      }),
    );
    const user = userEvent.setup();
    render(<InfrastructureResourceList sessionContext={sessionContext} />);
    await user.click(await screen.findByRole("button", { name: "Refresh" }));
    await screen.findByLabelText("Summary");
    expect(requests).toBe(2);
  });

  it("explains that the platform has not created any resources", async () => {
    server.use(...listHandlers({ summary: { total: 0, active: 0, activeBillable: 0, destroyed: 0 }, objects: [] }));
    render(<InfrastructureResourceList sessionContext={sessionContext} />);
    expect(await screen.findByText("The platform has not created any cloud resources yet.")).toBeInTheDocument();
  });

  it("says when only the most recent resources are listed", async () => {
    server.use(...listHandlers({ ...listResponse, summary: { ...listResponse.summary, total: 5000 } }));
    render(<InfrastructureResourceList sessionContext={sessionContext} />);
    expect(await screen.findByText(/Showing the 5 most recent of 5,000 resources/)).toBeInTheDocument();
  });

  it("shows why a user who is not a superuser is refused", async () => {
    server.use(...listForbiddenHandlers);
    render(<InfrastructureResourceList sessionContext={sessionContext} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Only superusers may see");
  });

  it("shows an error when the list cannot be loaded", async () => {
    server.use(...listErrorHandlers);
    render(<InfrastructureResourceList sessionContext={sessionContext} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Failed to load the infrastructure resources (500).");
  });
});

describe("filterResources", () => {
  it("matches the resource id and service, case-insensitively", () => {
    const filters = { ...defaultFilters, status: "all" as const };
    expect(filterResources(resources, { ...filters, text: "ARN:AWS:ACM" })).toHaveLength(1);
    expect(filterResources(resources, { ...filters, text: "kubernetes" })).toHaveLength(1);
    expect(filterResources([makeResource({ billable: false })], { ...filters, billableOnly: true })).toHaveLength(0);
  });
});

import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { manyResources, resources, sessionContext } from "@/mocks/fixtures";
import { listErrorHandlers, listForbiddenHandlers, listHandlers, listResponseFor } from "@/mocks/handlers";
import { server } from "@test/server";

import InfrastructureResourceList from "@/components/InfrastructureResourceList/Component";
import { defaultFilters, listRequest } from "@/components/InfrastructureResourceList/filters";

describe("InfrastructureResourceList", () => {
  it("summarizes the ledger, and lists the active resources", async () => {
    server.use(...listHandlers());
    render(<InfrastructureResourceList sessionContext={sessionContext} />);

    const summary = await screen.findByLabelText("Summary");
    expect(within(summary).getByLabelText("Active and billable: 3")).toBeInTheDocument();
    const row = screen.getByRole("row", { name: /customer\.example\.com.*dns\.zone.*aws/ });
    expect(within(row).getByText("dns.zone")).toBeInTheDocument();
    expect(within(row).getByText("Billable")).toBeInTheDocument();
    expect(within(row).getByText("Active")).toBeInTheDocument();
    // destroyed resources are not listed by default.
    expect(screen.queryByText("Destroyed", { selector: "span.badge" })).not.toBeInTheDocument();
    expect(screen.getByText("Showing 1–6 of 6 resources")).toBeInTheDocument();
  });

  it("filters by status, type, billable, provider and text", async () => {
    server.use(...listHandlers());
    const user = userEvent.setup();
    render(<InfrastructureResourceList sessionContext={sessionContext} />);

    await user.selectOptions(await screen.findByRole("combobox", { name: "Status" }), "destroyed");
    expect(await screen.findByText("Destroyed", { selector: "span.badge" })).toBeInTheDocument();
    expect(screen.getAllByRole("row")).toHaveLength(2);

    await user.selectOptions(screen.getByRole("combobox", { name: "Status" }), "all");
    await user.selectOptions(screen.getByRole("combobox", { name: "Type" }), "kubernetes.ingress");
    expect(await screen.findByText("Showing 1–1 of 1 resources")).toBeInTheDocument();
    expect(screen.getByText("example.3141-5926-5359.api.example.com")).toBeInTheDocument();

    await user.selectOptions(screen.getByRole("combobox", { name: "Type" }), "");
    await user.selectOptions(screen.getByRole("combobox", { name: "Provider" }), "memory");
    expect(await screen.findByText("local.example.com")).toBeInTheDocument();
    expect(screen.getAllByRole("row")).toHaveLength(2);

    await user.selectOptions(screen.getByRole("combobox", { name: "Provider" }), "");
    await user.click(screen.getByRole("checkbox", { name: "Billable only" }));
    expect(await screen.findByText("Showing 1–4 of 4 resources")).toBeInTheDocument();

    await user.type(screen.getByRole("searchbox", { name: "Search" }), "nothing matches this");
    expect(await screen.findByText("No resources match the filters.")).toBeInTheDocument();
  });

  it("lists every resource type of the ledger", async () => {
    server.use(...listHandlers());
    render(<InfrastructureResourceList sessionContext={sessionContext} />);
    const types = await screen.findByRole("combobox", { name: "Type" });
    const options = within(types)
      .getAllByRole("option")
      .map((option) => option.textContent);
    expect(options).toEqual([
      "All types",
      "certificate",
      "dns.record",
      "dns.zone",
      "kubernetes.ingress",
      "kubernetes.node",
      "kubernetes.persistentvolumeclaim",
    ]);
  });

  it("searches the whole ledger, not only the page", async () => {
    const requests: unknown[] = [];
    server.use(
      http.post(sessionContext.ApiUrl, async ({ request }) => {
        const body = (await request.json()) as Record<string, unknown>;
        requests.push(body);
        return HttpResponse.json(listResponseFor(manyResources, body));
      }),
    );
    const user = userEvent.setup();
    render(<InfrastructureResourceList sessionContext={sessionContext} />);
    await screen.findByText("node-1");
    await user.type(screen.getByRole("searchbox", { name: "Search" }), "node-119");
    expect(await screen.findByText("node-119")).toBeInTheDocument();
    expect(screen.getByText("Showing 1–1 of 1 resources")).toBeInTheDocument();
    // the search is requested once typing pauses, not for each keystroke.
    expect(requests.length).toBeLessThan("node-119".length);
    expect(requests.at(-1)).toMatchObject({ text: "node-119", page: 1 });
  });

  it("pages through the resources", async () => {
    server.use(...listHandlers(manyResources));
    const user = userEvent.setup();
    render(<InfrastructureResourceList sessionContext={sessionContext} />);

    expect(await screen.findByText("Showing 1–50 of 120 resources")).toBeInTheDocument();
    expect(screen.getByText("Page 1 of 3")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Previous" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "First" })).toBeDisabled();

    await user.click(screen.getByRole("button", { name: "Next" }));
    expect(await screen.findByText("Showing 51–100 of 120 resources")).toBeInTheDocument();
    expect(screen.getByText("node-51")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Last" }));
    expect(await screen.findByText("Showing 101–120 of 120 resources")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Next" })).toBeDisabled();

    await user.click(screen.getByRole("button", { name: "Previous" }));
    expect(await screen.findByText("Page 2 of 3")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "First" }));
    expect(await screen.findByText("Page 1 of 3")).toBeInTheDocument();

    await user.selectOptions(screen.getByRole("combobox", { name: "Rows per page" }), "25");
    expect(await screen.findByText("Showing 1–25 of 120 resources")).toBeInTheDocument();
    expect(screen.getByText("Page 1 of 5")).toBeInTheDocument();
  });

  it("returns to the first page when a filter changes", async () => {
    server.use(...listHandlers(manyResources));
    const user = userEvent.setup();
    render(<InfrastructureResourceList sessionContext={sessionContext} />);
    await user.click(await screen.findByRole("button", { name: "Next" }));
    await screen.findByText("Page 2 of 3");
    await user.click(screen.getByRole("checkbox", { name: "Billable only" }));
    expect(await screen.findByText("Page 1 of 3")).toBeInTheDocument();
  });

  it("refreshes the list", async () => {
    let requests = 0;
    server.use(
      http.post(sessionContext.ApiUrl, () => {
        requests += 1;
        return HttpResponse.json(listResponseFor(resources, {}));
      }),
    );
    const user = userEvent.setup();
    render(<InfrastructureResourceList sessionContext={sessionContext} />);
    await user.click(await screen.findByRole("button", { name: "Refresh" }));
    await screen.findByLabelText("Summary");
    expect(requests).toBe(2);
  });

  it("explains that the platform has not recorded any resources", async () => {
    server.use(...listHandlers([]));
    render(<InfrastructureResourceList sessionContext={sessionContext} />);
    expect(await screen.findByText("The platform has not recorded any cloud resources yet.")).toBeInTheDocument();
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

describe("listRequest", () => {
  it("sends the filters, the trimmed search, and the page", () => {
    expect(JSON.parse(listRequest({ ...defaultFilters, text: "  node  " }, 2, 25))).toEqual({
      ...defaultFilters,
      text: "node",
      page: 2,
      pageSize: 25,
    });
  });
});

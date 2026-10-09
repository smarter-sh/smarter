import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { delay, http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { server } from "@test/server";

import { makeCacheKey, writeCache } from "../../lib/cache";
import { API_URL, exampleContext, sessionContext } from "../../mocks/example";
import { examplePage, listErrorHandlers, listHandlers, manyExamples } from "../../mocks/handlers";
import TabbedListView from "./Component";

function setup() {
  render(<TabbedListView sessionContext={sessionContext} tabbedListViewContext={exampleContext} />);
  return userEvent.setup();
}

describe("TabbedListView", () => {
  it("loads, and shows, your objects, and those shared with you", async () => {
    server.use(...listHandlers());
    const user = setup();

    expect(screen.getByText("Loading 6 rows")).toBeInTheDocument();
    expect(await screen.findByText("first_example")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Shared Examples" }));
    expect(await screen.findByText("shared_example")).toBeInTheDocument();
    expect(screen.queryByText("first_example")).not.toBeInTheDocument();
  });

  it("switches to the card view, and remembers it", async () => {
    server.use(...listHandlers());
    const user = setup();
    await screen.findByText("first_example");

    await user.click(screen.getByRole("button", { name: "Thumbnail View" }));
    expect(screen.getByLabelText("Example cards")).toHaveTextContent("first_example");
    expect(sessionStorage.getItem("viewMode")).toBe("thumbnail");
  });

  it("shows cached objects at once", () => {
    server.use(...listHandlers());
    writeCache(makeCacheKey(API_URL, "owned"), [{ id: 9, name: "cached_example" }]);
    setup();
    expect(screen.getByText("cached_example")).toBeInTheDocument();
  });

  it("queries again, invalidating the backend's cache", async () => {
    const invalidations: (string | null)[] = [];
    server.use(
      http.post(`${API_URL}:tab/`, ({ request }) => {
        invalidations.push(new URL(request.url).searchParams.get("invalidate_cache"));
        return HttpResponse.json({ objects: [{ id: 1, name: "first_example" }] });
      }),
    );
    const user = setup();
    await screen.findByText("first_example");
    await vi.waitFor(() => expect(invalidations).toEqual(["false", "false"]));

    await user.click(screen.getByRole("button", { name: "Requery" }));
    await vi.waitFor(() => expect(invalidations).toEqual(["false", "false", "true", "true"]));
  });

  it("pages through a tab, with the previous and next buttons and the page number box", async () => {
    server.use(...listHandlers(manyExamples(30), [], 10));
    const user = setup();
    expect(await screen.findByText("example_1")).toBeInTheDocument();
    expect(screen.getByText("Showing 1–10 of 30")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Previous page" })).toBeDisabled();

    await user.click(screen.getByRole("button", { name: "Next page" }));
    expect(await screen.findByText("example_11")).toBeInTheDocument();
    expect(screen.queryByText("example_1")).not.toBeInTheDocument();
    expect(screen.getByText("Showing 11–20 of 30")).toBeInTheDocument();

    const input = screen.getByLabelText("Page number");
    await user.clear(input);
    await user.type(input, "3{Enter}");
    expect(await screen.findByText("example_21")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Next page" })).toBeDisabled();

    await user.click(screen.getByRole("button", { name: "Previous page" }));
    expect(await screen.findByText("example_11")).toBeInTheDocument();
  });

  it("remembers each tab's page", async () => {
    server.use(...listHandlers(manyExamples(30), manyExamples(5), 10));
    const user = setup();
    await screen.findByText("example_1");
    await user.click(screen.getByRole("button", { name: "Next page" }));
    await screen.findByText("example_11");

    await user.click(screen.getByRole("button", { name: "Shared Examples" }));
    expect(screen.getByText("Showing 1–5 of 5")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Your Examples" }));
    expect(screen.getByText("Showing 11–20 of 30")).toBeInTheDocument();
  });

  it("searches all of each tab's objects with the list api, from the first page", async () => {
    const searches: string[] = [];
    server.use(
      http.post(`${API_URL}:tab/`, ({ request, params }) => {
        const url = new URL(request.url);
        searches.push(`${params.tab}:${url.searchParams.get("page")}:${url.searchParams.get("search") ?? ""}`);
        const examples = params.tab === "owned" ? manyExamples(30) : [{ id: 99, name: "shared_example" }];
        return HttpResponse.json(examplePage(examples, request.url, 10));
      }),
    );
    const user = setup();
    await screen.findByText("example_1");
    await user.click(screen.getByRole("button", { name: "Next page" }));
    await screen.findByText("example_11");

    // example_2 and example_20 to example_29, of which example_29 is on the second page.
    await user.type(screen.getByRole("searchbox", { name: "Search" }), "example_2");
    expect(await screen.findByText("Showing 1–10 of 11")).toBeInTheDocument();
    expect(screen.getByText("example_2")).toBeInTheDocument();
    expect(screen.queryByText("example_11")).not.toBeInTheDocument();
    expect(searches).toContain("owned:1:example_2");
    expect(searches).toContain("shared:1:example_2");
    // a search is requested once typing pauses, rather than for every keystroke.
    expect(searches.filter((search) => search.startsWith("owned:1:example"))).toEqual(["owned:1:example_2"]);

    await user.click(screen.getByRole("button", { name: "Next page" }));
    expect(await screen.findByText("example_29")).toBeInTheDocument();
    expect(searches).toContain("owned:2:example_2");

    // nothing that is shared matches, so the shared tab has no pager.
    await user.click(screen.getByRole("button", { name: "Shared Examples" }));
    expect(screen.queryByText("shared_example")).not.toBeInTheDocument();
    expect(screen.queryByRole("navigation", { name: "Pagination" })).not.toBeInTheDocument();
  });

  it("does not cache a page of a search", async () => {
    server.use(...listHandlers(manyExamples(30), [], 10));
    const user = setup();
    await screen.findByText("example_1");
    await user.type(screen.getByRole("searchbox", { name: "Search" }), "example_3");
    expect(await screen.findByText("Showing 1–2 of 2")).toBeInTheDocument();
    const cached = JSON.parse(sessionStorage.getItem(makeCacheKey(API_URL, "owned")) ?? "{}");
    expect(cached.objects).toHaveLength(10);
  });

  it("shows only the latest search, when an earlier one responds later", async () => {
    server.use(
      http.post(`${API_URL}:tab/`, async ({ request }) => {
        if (new URL(request.url).searchParams.get("search") === "slow") {
          await delay(600);
          return HttpResponse.json({ objects: [{ id: 7, name: "slow_example" }] });
        }
        return HttpResponse.json(examplePage(manyExamples(3), request.url));
      }),
    );
    const user = setup();
    await screen.findByText("example_1");
    const searchbox = screen.getByRole("searchbox", { name: "Search" });
    await user.type(searchbox, "slow");
    await new Promise((resolve) => setTimeout(resolve, 400));
    await user.clear(searchbox);
    expect(await screen.findByText("example_1")).toBeInTheDocument();
    await new Promise((resolve) => setTimeout(resolve, 600));
    expect(screen.queryByText("slow_example")).not.toBeInTheDocument();
  });

  it("shows the api's error", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    server.use(...listErrorHandlers);
    setup();
    expect(await screen.findByRole("alert")).toHaveTextContent("Database unavailable");
  });
});

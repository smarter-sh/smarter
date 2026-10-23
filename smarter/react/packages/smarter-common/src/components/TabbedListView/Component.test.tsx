import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { delay, http, HttpResponse } from "msw";
import { afterEach, describe, expect, it, vi } from "vitest";

import { server } from "@test/server";

import { makeCacheKey, readCache, sessionScope, writeCache } from "../../lib/cache";
import { API_URL, exampleContext, exampleContextWithOtherTab, sessionContext } from "../../mocks/example";
import { examplePage, listErrorHandlers, listHandlers, manyExamples, otherHandler } from "../../mocks/handlers";
import TabbedListView from "./Component";

/** The rows of the example list view. */
function rows() {
  return within(screen.getByRole("list", { name: "Examples" })).getAllByRole("listitem");
}

/** The cache key of a page of a tab, as the list writes it. */
function key(tab: string, query: { page?: number; ordering?: string; filter?: string } = {}) {
  return makeCacheKey(API_URL, tab, query, sessionScope(sessionContext));
}

function setup() {
  render(<TabbedListView sessionContext={sessionContext} tabbedListViewContext={exampleContext} />);
  return userEvent.setup();
}

describe("TabbedListView", () => {
  afterEach(() => {
    window.history.replaceState(null, "", "/");
  });

  it("opens narrowed by the named filter of the page's url, and shows all again", async () => {
    const filters: string[] = [];
    server.use(
      http.post(`${API_URL}:tab/`, ({ request }) => {
        filters.push(new URL(request.url).searchParams.get("filter") ?? "");
        return HttpResponse.json(examplePage(manyExamples(6), request.url));
      }),
    );
    window.history.replaceState(null, "", "/examples/?filter=even&tab=owned");
    const user = setup();

    expect(screen.getByText("Showing: Even examples")).toBeInTheDocument();
    expect(await screen.findByText("example_2")).toBeInTheDocument();
    const names = () =>
      rows()
        .map((row) => row.textContent)
        .filter((text) => text?.startsWith("example_"));
    expect(names()).toEqual(["example_2", "example_4", "example_6"]);
    await vi.waitFor(() => expect(filters).toEqual(["even", "even"]));

    await user.click(screen.getByRole("button", { name: "Show all" }));
    expect(await screen.findByText("example_1")).toBeInTheDocument();
    expect(names()).toHaveLength(6);
    expect(screen.queryByText("Showing: Even examples")).not.toBeInTheDocument();
    expect(window.location.search).toBe("?tab=owned");
    await vi.waitFor(() => expect(filters).toEqual(["even", "even", "", ""]));
  });

  it("caches a filtered page apart from the unfiltered one", async () => {
    server.use(
      http.post(`${API_URL}:tab/`, ({ request }) => HttpResponse.json(examplePage(manyExamples(4), request.url))),
    );
    writeCache(key("owned"), [{ id: 9, name: "cached_example" }]);
    window.history.replaceState(null, "", "/?filter=even");
    setup();
    expect(screen.queryByText("cached_example")).not.toBeInTheDocument();
    expect(await screen.findByText("example_2")).toBeInTheDocument();
    expect(readCache(key("owned"))?.objects).toEqual([{ id: 9, name: "cached_example" }]);
    await vi.waitFor(() =>
      expect(readCache<{ name: string }>(key("owned", { filter: "even" }))?.objects.map((o) => o.name)).toEqual([
        "example_2",
        "example_4",
      ]),
    );
  });

  it("drops a filter that the list api doesn't offer", async () => {
    server.use(
      http.post(`${API_URL}:tab/`, ({ request }) => HttpResponse.json(examplePage(manyExamples(3), request.url))),
    );
    window.history.replaceState(null, "", "/?filter=nonsense");
    setup();
    expect(screen.getByText("Showing: nonsense")).toBeInTheDocument();
    expect(await screen.findByText("example_1")).toBeInTheDocument();
    expect(screen.queryByText(/^Showing: /)).not.toBeInTheDocument();
  });

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

  it("shows cached objects at once, refreshing them", async () => {
    server.use(...listHandlers());
    writeCache(key("owned"), [{ id: 9, name: "cached_example" }]);
    setup();
    expect(screen.getByText("cached_example")).toBeInTheDocument();
    expect(screen.getByRole("status", { name: "Refreshing" })).toBeInTheDocument();
    expect(await screen.findByText("first_example")).toBeInTheDocument();
    expect(screen.queryByText("cached_example")).not.toBeInTheDocument();
    expect(screen.queryByRole("status", { name: "Refreshing" })).not.toBeInTheDocument();
  });

  it("shows a page seen before at once, when paging back to it", async () => {
    server.use(
      http.post(`${API_URL}:tab/`, async ({ request }) => {
        await delay(200);
        return HttpResponse.json(examplePage(manyExamples(12), request.url, 10));
      }),
    );
    const user = setup();
    expect(await screen.findByText("example_1")).toBeInTheDocument();
    await vi.waitFor(() => expect(readCache(key("owned"))).not.toBeNull());
    await user.click(screen.getByRole("button", { name: "Next page" }));
    expect(await screen.findByText("example_11")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Previous page" }));
    // from the cache, before the 200 ms response.
    expect(screen.getByText("example_1")).toBeInTheDocument();
    expect(screen.getByRole("status", { name: "Refreshing" })).toBeInTheDocument();
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

  it("queries again from the Refresh button, invalidating the backend's cache", async () => {
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
    const refresh = screen.getByRole("button", { name: "Refresh" });
    await vi.waitFor(() => expect(refresh).toBeEnabled());

    await user.click(refresh);
    await vi.waitFor(() => expect(invalidations).toEqual(["false", "false", "true", "true"]));
  });

  it("disables the Refresh button while the list loads", async () => {
    server.use(
      http.post(`${API_URL}:tab/`, async () => {
        await delay(200);
        return HttpResponse.json({ objects: [{ id: 1, name: "first_example" }] });
      }),
    );
    setup();
    expect(screen.getByRole("button", { name: "Refresh" })).toBeDisabled();
    await screen.findByText("first_example");
    expect(screen.getByRole("button", { name: "Refresh" })).toBeEnabled();
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

  it("sorts all of each tab's objects with the list api, from the first page", async () => {
    const requests: string[] = [];
    server.use(
      http.post(`${API_URL}:tab/`, ({ request, params }) => {
        const url = new URL(request.url);
        requests.push(`${params.tab}:${url.searchParams.get("page")}:${url.searchParams.get("ordering") ?? ""}`);
        return HttpResponse.json(examplePage(params.tab === "owned" ? manyExamples(30) : [], request.url, 10));
      }),
    );
    const user = setup();
    await screen.findByText("example_1");
    // the list api can sort by name, but not by id.
    expect(screen.queryByRole("button", { name: "Id" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Next page" }));
    await screen.findByText("example_11");

    // ascending, by name: example_1, example_10, ..., example_18 on the first page.
    await user.click(screen.getByRole("button", { name: "Name" }));
    expect(await screen.findByText("example_1")).toBeInTheDocument();
    expect(rows()[1]).toHaveTextContent("example_10");
    expect(screen.getByText("Showing 1–10 of 30")).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Name" })).toHaveAttribute("aria-sort", "ascending");
    expect(requests).toContain("owned:1:name");
    expect(requests).toContain("shared:1:name");

    // the sort holds while paging: the second page continues it.
    await user.click(screen.getByRole("button", { name: "Next page" }));
    expect(await screen.findByText("example_25")).toBeInTheDocument();
    expect(requests).toContain("owned:2:name");

    // descending, by name: example_9, example_8, ..., example_3, example_30, example_29, ...
    await user.click(screen.getByRole("button", { name: "Name" }));
    expect(await screen.findByText("example_30")).toBeInTheDocument();
    expect(rows()[0]).toHaveTextContent("example_9");
    expect(screen.getByRole("columnheader", { name: "Name" })).toHaveAttribute("aria-sort", "descending");
    expect(requests).toContain("owned:1:-name");

    // and then the list api's default order.
    await user.click(screen.getByRole("button", { name: "Name" }));
    expect(await screen.findByText("example_2")).toBeInTheDocument();
    expect(rows()[0]).toHaveTextContent("example_1");
    expect(screen.getByRole("columnheader", { name: "Name" })).toHaveAttribute("aria-sort", "none");
    expect(requests.at(-1)).toMatch(/:1:$/);
  });

  it("caches a sorted page apart from the default order, and queries again in the same order", async () => {
    const orderings: string[] = [];
    server.use(
      http.post(`${API_URL}:tab/`, ({ request }) => {
        orderings.push(new URL(request.url).searchParams.get("ordering") ?? "");
        return HttpResponse.json(examplePage(manyExamples(12), request.url, 10));
      }),
    );
    const user = setup();
    await screen.findByText("example_1");
    await user.click(screen.getByRole("button", { name: "Name" }));
    await user.click(await screen.findByRole("button", { name: "Name" }));
    expect(await screen.findByText("example_9")).toBeInTheDocument();
    expect(rows()[0]).toHaveTextContent("example_9");
    expect(readCache<{ name: string }>(key("owned"))?.objects[0].name).toBe("example_1");
    await vi.waitFor(() =>
      expect(readCache<{ name: string }>(key("owned", { ordering: "-name" }))?.objects[0].name).toBe("example_9"),
    );

    await vi.waitFor(() => expect(orderings.filter((ordering) => ordering === "-name")).toHaveLength(2));
    orderings.length = 0;
    await user.click(screen.getByRole("button", { name: "Requery" }));
    await vi.waitFor(() => expect(orderings).toEqual(["-name", "-name"]));
  });

  it("does not cache a page of a search", async () => {
    server.use(...listHandlers(manyExamples(30), [], 10));
    const user = setup();
    await screen.findByText("example_1");
    await user.type(screen.getByRole("searchbox", { name: "Search" }), "example_3");
    expect(await screen.findByText("Showing 1–2 of 2")).toBeInTheDocument();
    expect(readCache(key("owned"))?.objects).toHaveLength(10);
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

  describe("with a tab of its own object type and views", () => {
    it("loads the tab from its own slug of the list api, and shows it with its own views", async () => {
      server.use(...listHandlers(), otherHandler());
      render(<TabbedListView sessionContext={sessionContext} tabbedListViewContext={exampleContextWithOtherTab} />);
      const user = userEvent.setup();
      await screen.findByText("first_example");
      expect(screen.getByRole("searchbox", { name: "Search" })).toHaveAttribute("placeholder", "Search examples");

      await user.click(screen.getByRole("button", { name: "Others" }));
      expect(within(screen.getByRole("list", { name: "Others" })).getByText("An other object")).toBeInTheDocument();
      expect(screen.queryByText("first_example")).not.toBeInTheDocument();
      expect(screen.getByRole("searchbox", { name: "Search" })).toHaveAttribute("placeholder", "Search others");

      await user.click(screen.getByRole("button", { name: "Thumbnail View" }));
      expect(screen.getByLabelText("Other cards")).toHaveTextContent("An other object");
    });

    it("searches the tab too", async () => {
      const searches: string[] = [];
      server.use(
        ...listHandlers(),
        http.post(`${API_URL}others/`, ({ request }) => {
          searches.push(new URL(request.url).searchParams.get("search") ?? "");
          return HttpResponse.json({ objects: [] });
        }),
      );
      render(<TabbedListView sessionContext={sessionContext} tabbedListViewContext={exampleContextWithOtherTab} />);
      const user = userEvent.setup();
      await screen.findByText("first_example");
      await user.type(screen.getByRole("searchbox", { name: "Search" }), "other");
      await vi.waitFor(() => expect(searches).toEqual(["", "other"]));
    });
  });
});

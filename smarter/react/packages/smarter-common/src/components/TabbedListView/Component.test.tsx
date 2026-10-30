import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { delay, http, HttpResponse } from "msw";
import { afterEach, describe, expect, it, vi } from "vitest";

import { server } from "@test/server";

import { makeCacheKey, readCache, sessionScope, writeCache } from "../../lib/cache";
import {
  API_URL,
  exampleContext,
  exampleContextWithOtherTab,
  ownedExamples,
  sessionContext,
  sharedExamples,
} from "../../mocks/example";
import {
  detailHandler,
  examplePage,
  listErrorHandlers,
  listHandlers,
  manyExamples,
  otherHandler,
} from "../../mocks/handlers";
import TabbedListView from "./Component";

/** The rows of the example list view's table, but its header. */
function rows() {
  return within(screen.getByRole("table", { name: "Examples" }))
    .getAllByRole("row")
    .slice(1);
}

/** The names of the rows: the text of their first cells. */
function rowNames() {
  return rows().map((row) => (row as HTMLTableRowElement).cells[0].textContent);
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
    const names = () => rowNames().filter((text) => text?.startsWith("example_"));
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
      expect(within(screen.getByRole("table", { name: "Others" })).getByText("An other object")).toBeInTheDocument();
      expect(screen.queryByText("first_example")).not.toBeInTheDocument();
      expect(screen.getByRole("searchbox", { name: "Search" })).toHaveAttribute("placeholder", "Search others");

      // the tab's rows open its own DetailView, which has no other tabs: its objects have no detailUrl.
      await user.click(screen.getByText("An other object"));
      const dialog = await screen.findByRole("dialog", { name: "An other object" });
      expect(within(dialog).getByText("Title")).toBeInTheDocument();
      expect(
        within(dialog)
          .getAllByRole("tab")
          .map((tab) => tab.textContent),
      ).toEqual(["Details"]);
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

describe("TabbedListView narrowing by tags and annotations", () => {
  afterEach(() => {
    window.history.replaceState(null, "", "/");
  });

  /** The names of the example rows that the list view shows. */
  function names() {
    return rowNames().filter((text) => text?.endsWith("_example"));
  }

  /** A row of the list view, by its example's name. */
  function row(name: string) {
    return within(rows().find((item) => (item as HTMLTableRowElement).cells[0].textContent === name)!);
  }

  /** The tag and annotation parameters of the list api's requests. */
  function recordRequests() {
    const requests: string[] = [];
    server.use(
      http.post(`${API_URL}:tab/`, ({ request }) => {
        const params = new URL(request.url).searchParams;
        if (request.url.includes("/owned/")) {
          requests.push(JSON.stringify([params.getAll("tag"), params.getAll("annotation")]));
        }
        return HttpResponse.json(
          examplePage(request.url.includes("/owned/") ? ownedExamples : sharedExamples, request.url),
        );
      }),
    );
    return requests;
  }

  it("narrows by a tag clicked in a row, shows it as a chip, keeps it in the url, and removes it", async () => {
    const requests = recordRequests();
    const user = setup();
    await screen.findByText("first_example");

    await user.click(row("first_example").getByRole("button", { name: "red" }));
    expect(await screen.findByText("Tag: red")).toBeInTheDocument();
    // the chip narrows the list, rather than open the row's detail.
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    await waitFor(() => expect(names()).toEqual(["first_example"]));
    expect(new URLSearchParams(window.location.search).getAll("tag")).toEqual(["red"]);
    // the tag that narrows the list shows as pressed.
    expect(row("first_example").getByRole("button", { name: "red" })).toHaveAttribute("aria-pressed", "true");
    expect(requests).toContain(JSON.stringify([["red"], []]));

    await user.click(screen.getByRole("button", { name: "Remove Tag: red" }));
    await waitFor(() => expect(names()).toEqual(["first_example", "second_example"]));
    expect(window.location.search).toBe("");
  });

  it("narrows by an annotation clicked in a row", async () => {
    recordRequests();
    const user = setup();
    await screen.findByText("second_example");
    await user.click(row("second_example").getByRole("button", { name: "example.com/team: b" }));
    expect(await screen.findByText("Annotation: example.com/team=b")).toBeInTheDocument();
    await waitFor(() => expect(names()).toEqual(["second_example"]));
    expect(new URLSearchParams(window.location.search).getAll("annotation")).toEqual(["example.com/team=b"]);
  });

  it("narrows by a tag clicked in a row's detail, and closes the detail", async () => {
    recordRequests();
    server.use(detailHandler());
    const user = setup();
    await user.click(await screen.findByText("first_example"));
    const dialog = await screen.findByRole("dialog", { name: "first_example" });
    await user.click(within(dialog).getByRole("button", { name: "red" }));
    expect(await screen.findByText("Tag: red")).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("opens narrowed by the tags, annotations and search of the page's url", async () => {
    const requests = recordRequests();
    window.history.replaceState(null, "", "/examples/?annotation=example.com/team%3Da&tag=red&tag=red&search=first");
    setup();
    expect(screen.getByText("Tag: red")).toBeInTheDocument();
    expect(screen.getByText("Annotation: example.com/team=a")).toBeInTheDocument();
    expect(screen.getByRole("searchbox", { name: "Search" })).toHaveValue("first");
    await waitFor(() => expect(names()).toEqual(["first_example"]));
    expect(requests[0]).toBe(JSON.stringify([["red"], ["example.com/team=a"]]));
  });

  it("adds a typed annotation requirement with Enter, and shows why the list api rejects one", async () => {
    recordRequests();
    const user = setup();
    await screen.findByText("first_example");
    const box = screen.getByRole("textbox", { name: "Filter by annotation" });

    await user.type(box, "example.com/team=a{Enter}");
    expect(box).toHaveValue("");
    expect(await screen.findByText("Annotation: example.com/team=a")).toBeInTheDocument();
    await waitFor(() => expect(names()).toEqual(["first_example"]));

    // a blank requirement, and one that is already applied, add nothing.
    await user.type(box, "   {Enter}");
    await user.type(box, "example.com/team=a{Enter}");
    expect(screen.getAllByText(/^Annotation: /)).toHaveLength(1);

    await user.type(box, "bad key{Enter}");
    expect(await screen.findByRole("alert")).toHaveTextContent("Annotation key 'bad key' is invalid.");
    expect(box).toHaveAttribute("aria-invalid", "true");

    await user.click(screen.getByRole("button", { name: "Remove Annotation: bad key" }));
    await waitFor(() => expect(screen.queryByRole("alert")).not.toBeInTheDocument());
    expect(new URLSearchParams(window.location.search).getAll("annotation")).toEqual(["example.com/team=a"]);
  });

  it("caches a narrowed page under its own key", async () => {
    recordRequests();
    window.history.replaceState(null, "", "/examples/?tag=blue");
    setup();
    await waitFor(() => expect(names()).toEqual(["second_example"]));
    expect(
      readCache(makeCacheKey(API_URL, "owned", { tags: ["blue"] }, sessionScope(sessionContext)))?.objects,
    ).toEqual([ownedExamples[1]]);
    expect(readCache(key("owned"))).toBeNull();
  });
});

describe("TabbedListView's resource detail", () => {
  afterEach(() => {
    window.history.replaceState(null, "", "/");
  });

  /** The detail dialog, by the name of its resource. */
  const dialog = (name: string) => screen.findByRole("dialog", { name });

  it("opens a row's detail when the row is clicked, with its DetailView, and closes it", async () => {
    server.use(...listHandlers(), detailHandler());
    const user = setup();
    await user.click(await screen.findByText("first_example"));

    const detail = within(await dialog("first_example"));
    expect(detail.getByText("The first example.")).toBeInTheDocument();
    expect(detail.getAllByRole("tab").map((tab) => tab.textContent?.replace(/\d+$/, ""))).toEqual([
      "Details",
      "Manifest",
      "Hierarchy",
      "Dependencies",
    ]);
    expect(detail.getByRole("tab", { name: "Details" })).toHaveAttribute("aria-selected", "true");
    expect(detail.getByText("1 of 2")).toBeInTheDocument();
    // the row whose detail is open stands out.
    expect(rows()[0]).toHaveClass("smarter-row-selected");
    // the kind, once the detail is loaded.
    expect(await detail.findByText("Guardrail")).toBeInTheDocument();

    await user.click(detail.getByRole("button", { name: "Close" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("opens a focused row's detail with Enter, and closes it with Escape", async () => {
    server.use(...listHandlers(), detailHandler());
    const user = setup();
    await screen.findByText("second_example");
    await waitFor(() => expect(rows()[1]).toHaveAttribute("tabindex", "0"));
    rows()[1].focus();
    await user.keyboard("{Enter}");
    expect(await dialog("second_example")).toBeInTheDocument();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("shows the manifest, the hierarchy and the dependencies", async () => {
    server.use(...listHandlers(), detailHandler());
    const user = setup();
    await user.click(await screen.findByText("first_example"));
    const detail = within(await dialog("first_example"));

    await user.click(detail.getByRole("tab", { name: /Manifest/ }));
    const manifest = await detail.findByLabelText("Manifest YAML");
    expect(manifest).toHaveTextContent("apiVersion: smarter.sh/v1");
    expect(within(manifest).getByText("apiVersion")).toHaveClass("yaml-key");
    expect(detail.getByRole("link", { name: "Edit manifest" })).toHaveAttribute("href", "/guardrail/guardrails/r1/");

    await user.click(detail.getByRole("tab", { name: /Hierarchy/ }));
    expect(detail.getByText("first_example uses 2 resources, 2 levels deep.")).toBeInTheDocument();
    expect(detail.getByRole("tab", { name: /Hierarchy/ })).toHaveTextContent("2");
    await user.click(detail.getByRole("button", { name: "Collapse all" }));
    expect(detail.getByRole("button", { name: "Expand all" })).toBeEnabled();

    await user.click(detail.getByRole("tab", { name: /Dependencies/ }));
    expect(detail.getByText(/2 resources use first_example/)).toBeInTheDocument();
    const dependents = detail.getByRole("list", { name: "What uses first_example" });
    expect(within(dependents).getByText("stackademy_sql")).toBeInTheDocument();
    expect(within(dependents).getByText("You can't read this resource")).toBeInTheDocument();
  });

  it("says when nothing depends on the resource", async () => {
    server.use(...listHandlers(), detailHandler([]));
    const user = setup();
    await user.click(await screen.findByText("first_example"));
    const detail = within(await dialog("first_example"));
    await user.click(detail.getByRole("tab", { name: /Dependencies/ }));
    expect(await detail.findByText("No other resource uses first_example.")).toBeInTheDocument();
  });

  it("reports a detail that fails to load, and tries again", async () => {
    let calls = 0;
    server.use(
      ...listHandlers(),
      http.post("/dashboard/api/resource/Example/:locator/", () => {
        calls += 1;
        return HttpResponse.json({ error: "Guardrail not found." }, { status: 404 });
      }),
    );
    const user = setup();
    await user.click(await screen.findByText("first_example"));
    const detail = within(await dialog("first_example"));
    await user.click(detail.getByRole("tab", { name: /Manifest/ }));
    expect(await detail.findByRole("alert")).toHaveTextContent("Guardrail not found.");
    await user.click(detail.getByRole("button", { name: "Try again" }));
    await vi.waitFor(() => expect(calls).toBe(2));
  });

  it("browses the page with Previous and Next, and the arrow keys, keeping the tab that is open", async () => {
    server.use(...listHandlers(), detailHandler());
    const user = setup();
    await user.click(await screen.findByText("first_example"));
    let detail = within(await dialog("first_example"));
    expect(detail.getByRole("button", { name: "Previous" })).toBeDisabled();
    await user.click(detail.getByRole("tab", { name: /Manifest/ }));

    await user.click(detail.getByRole("button", { name: "Next" }));
    detail = within(await dialog("second_example"));
    expect(detail.getByText("2 of 2")).toBeInTheDocument();
    expect(detail.getByRole("tab", { name: /Manifest/ })).toHaveAttribute("aria-selected", "true");
    expect(await detail.findByLabelText("Manifest YAML")).toHaveTextContent("name: second_example");
    expect(detail.getByRole("button", { name: "Next" })).toBeDisabled();

    await user.keyboard("{ArrowLeft}");
    expect(await dialog("first_example")).toBeInTheDocument();
    await user.keyboard("{ArrowRight}");
    expect(await dialog("second_example")).toBeInTheDocument();
  });

  it("moves between the tabs of the detail with the arrow keys of its tab list", async () => {
    server.use(...listHandlers(), detailHandler());
    const user = setup();
    await user.click(await screen.findByText("first_example"));
    const detail = within(await dialog("first_example"));
    detail.getByRole("tab", { name: "Details" }).focus();
    await user.keyboard("{ArrowRight}");
    expect(detail.getByRole("tab", { name: /Manifest/ })).toHaveAttribute("aria-selected", "true");
    // the arrow keys of the tab list don't browse the list.
    expect(screen.getByRole("dialog", { name: "first_example" })).toBeInTheDocument();
    await user.keyboard("{ArrowLeft}{ArrowLeft}");
    expect(detail.getByRole("tab", { name: /Dependencies/ })).toHaveAttribute("aria-selected", "true");
  });

  it("browses on to the next page, and back to the previous one", async () => {
    server.use(...listHandlers(manyExamples(12), [], 10), detailHandler());
    const user = setup();
    await screen.findByText("example_10");
    await user.click(rows()[9]);
    let detail = within(await dialog("example_10"));
    expect(detail.getByText("10 of 12")).toBeInTheDocument();

    await user.click(detail.getByRole("button", { name: "Next" }));
    detail = within(await dialog("example_11"));
    expect(detail.getByText("11 of 12")).toBeInTheDocument();
    expect(screen.getByText("example_12")).toBeInTheDocument();

    await user.click(detail.getByRole("button", { name: "Previous" }));
    expect(await dialog("example_10")).toBeInTheDocument();
    expect(screen.getByText("example_1")).toBeInTheDocument();
  });

  it("closes the detail when the tab or the search changes", async () => {
    server.use(...listHandlers(), detailHandler());
    const user = setup();
    await user.click(await screen.findByText("first_example"));
    expect(await dialog("first_example")).toBeInTheDocument();
    await user.keyboard("{Escape}");

    await user.click(screen.getByText("second_example"));
    expect(await dialog("second_example")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Close" }));
    await user.type(screen.getByRole("searchbox", { name: "Search" }), "first");
    await waitFor(() => expect(rowNames()).toEqual(["first_example"]));
    await user.click(screen.getByText("first_example"));
    expect(await dialog("first_example")).toBeInTheDocument();
    await user.clear(screen.getByRole("searchbox", { name: "Search" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });

  it("leaves a row's text selected rather than open its detail", async () => {
    server.use(...listHandlers(), detailHandler());
    const user = setup();
    const cell = await screen.findByText("first_example");
    const selection = vi.spyOn(window, "getSelection").mockReturnValue({ toString: () => "first" } as Selection);
    await user.click(cell);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    selection.mockRestore();
  });
});

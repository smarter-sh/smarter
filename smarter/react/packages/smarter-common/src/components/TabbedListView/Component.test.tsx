import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { server } from "@test/server";

import { makeCacheKey, writeCache } from "../../lib/cache";
import { API_URL, exampleContext, sessionContext } from "../../mocks/example";
import { listErrorHandlers, listHandlers } from "../../mocks/handlers";
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

  it("shows the api's error", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    server.use(...listErrorHandlers);
    setup();
    expect(await screen.findByRole("alert")).toHaveTextContent("Database unavailable");
  });
});

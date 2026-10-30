import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { appContext, globalSearchResponse } from "@/mocks/fixtures";
import { globalSearchHandler } from "@/mocks/handlers";
import { server } from "@test/server";

import GlobalSearch from "@/components/GlobalSearch/Component";

const apiUrl = appContext.globalSearchApiUrl;

function setup() {
  render(<GlobalSearch sessionContext={appContext.sessionContext} apiUrl={apiUrl} />);
  return { user: userEvent.setup(), box: screen.getByRole("searchbox", { name: "Search every resource" }) };
}

describe("GlobalSearch", () => {
  it("shows nothing until something is typed, and explains the syntax", () => {
    setup();
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    expect(screen.getByText(/tag:production/)).toBeInTheDocument();
  });

  it("groups the results by list, links each one, and links a list with more to its narrowed page", async () => {
    const queries: string[] = [];
    server.use(
      http.post(apiUrl, async ({ request }) => {
        queries.push(((await request.json()) as { query: string }).query);
        return HttpResponse.json(globalSearchResponse);
      }),
    );
    const { user, box } = setup();
    await user.type(box, "tag:production");

    expect(await screen.findByRole("status")).toHaveTextContent("7 resources match.");
    // the search is requested once typing pauses, not for every keystroke.
    expect(queries).toEqual(["tag:production"]);
    const guardrails = within(screen.getByRole("list", { name: "Guardrails" }));
    expect(guardrails.getAllByRole("link")).toHaveLength(5);
    expect(guardrails.getByRole("link", { name: "guardrail_1" })).toHaveAttribute("href", "/guardrail/guardrails/r1x/");
    expect(screen.getByRole("link", { name: "See all 6 in Guardrails" })).toHaveAttribute(
      "href",
      "/guardrail/?tag=production",
    );
    // a list whose results are all shown has no "See all" link.
    expect(screen.queryByRole("link", { name: /See all 1 in Secrets/ })).not.toBeInTheDocument();
  });

  it("says when nothing matches", async () => {
    server.use(globalSearchHandler);
    const { user, box } = setup();
    await user.type(box, "nothing");
    expect(await screen.findByRole("status")).toHaveTextContent("Nothing matches nothing.");
  });

  it("shows why an annotation selector is invalid", async () => {
    server.use(globalSearchHandler);
    const { user, box } = setup();
    await user.type(box, "Bad Key=x");
    expect(await screen.findByRole("alert")).toHaveTextContent("invalid name segment");
  });

  it("shows a failed request, and clears the results when the box is emptied", async () => {
    server.use(http.post(apiUrl, () => HttpResponse.json({}, { status: 503 })));
    const { user, box } = setup();
    await user.type(box, "support");
    expect(await screen.findByRole("alert")).toHaveTextContent("Search failed: Request failed: 503");
    await user.clear(box);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});

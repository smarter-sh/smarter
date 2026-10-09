import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { makeObject, sessionContext } from "@/mocks/fixtures";
import type { Proxy } from "@/lib/Types";

import CardView from "@/components/CardView/Component";

/** The value of a card's detail row, by its label. */
function detail(label: string) {
  const row = screen
    .getAllByRole("row")
    .find((r) => within(r).queryAllByRole("cell")[0]?.textContent?.startsWith(label));
  return within(row!).getAllByRole("cell")[1];
}

describe("CardView", () => {
  it("shows a Proxy that allows every path, without headers", () => {
    render(<CardView sessionContext={sessionContext} objects={[makeObject(1)]} onRequery={() => {}} />);
    expect(detail("Headers")).toHaveTextContent("No value");
    expect(detail("Allowed Paths")).toHaveTextContent("All paths");
  });

  it("shows a Proxy's headers and allowed paths", () => {
    const proxy = makeObject(1, { headers: { "x-org": "smarter" }, allowedPaths: ["/v1/chat/completions"] });
    render(<CardView sessionContext={sessionContext} objects={[proxy]} onRequery={() => {}} />);
    expect(detail("Headers")).toHaveTextContent('"x-org": "smarter"');
    expect(detail("Allowed Paths")).toHaveTextContent("/v1/chat/completions");
  });

  it("shows a Proxy without headers, paths or owner", () => {
    const proxy = makeObject(1, { headers: undefined, allowedPaths: undefined, userProfile: undefined } as never);
    render(<CardView sessionContext={sessionContext} objects={[proxy]} onRequery={() => {}} />);
    expect(detail("Headers")).toHaveTextContent("No value");
    expect(detail("Owner")).toHaveTextContent("No value");
  });

  it("shows nothing without a list of objects", () => {
    render(<CardView sessionContext={sessionContext} objects={null as unknown as Proxy[]} onRequery={() => {}} />);
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });
});

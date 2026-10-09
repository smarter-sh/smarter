import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { SERIES_URL, makeResourceStatus, series, sessionContext } from "@/mocks/fixtures";
import { server } from "@test/server";

import ResourceChart from "./ResourceChart";

vi.mock("recharts", async (importOriginal) => (await import("@test/recharts")).withFixedSize(await importOriginal()));

describe("ResourceChart", () => {
  it("charts the resource's series for its budget", async () => {
    server.use(
      http.post(SERIES_URL, () =>
        HttpResponse.json([
          { status: { budget: "another_budget" }, series: [] },
          { status: { budget: "monthly_llm_budget" }, series },
        ]),
      ),
    );
    render(<ResourceChart sessionContext={sessionContext} status={makeResourceStatus()} />);
    expect(screen.getByText("Loading…")).toBeInTheDocument();
    expect(await screen.findByText("Apr 2026")).toBeInTheDocument();
  });

  it("charts no periods when the series has none for its budget", async () => {
    server.use(http.post(SERIES_URL, () => HttpResponse.json([])));
    render(<ResourceChart sessionContext={sessionContext} status={makeResourceStatus()} />);
    await vi.waitFor(() => expect(screen.queryByText("Loading…")).not.toBeInTheDocument());
    expect(screen.queryByText(/failed/i)).not.toBeInTheDocument();
  });

  it("says when the series fails to load", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    server.use(http.post(SERIES_URL, () => new HttpResponse(null, { status: 500 })));
    render(<ResourceChart sessionContext={sessionContext} status={makeResourceStatus()} />);
    expect(await screen.findByText("Failed to load the budget series (500).")).toBeInTheDocument();
  });
});

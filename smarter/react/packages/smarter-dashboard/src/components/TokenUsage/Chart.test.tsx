import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { appContext, sessionContext, tokenUsage } from "@/mocks/fixtures";
import { server } from "@test/server";

import TokenUsageChart from "@/components/TokenUsage/Chart";

vi.mock("recharts", async (importOriginal) => (await import("@test/recharts")).withFixedSize(await importOriginal()));

const apiUrl = appContext.chargesApiUrl;

describe("TokenUsageChart", () => {
  it("charts the token usage, and reloads it for another periodicity", async () => {
    const requested: string[] = [];
    server.use(
      http.post(`${apiUrl}:periodicity/`, ({ params }) => {
        requested.push(String(params.periodicity));
        return HttpResponse.json(tokenUsage);
      }),
    );
    const user = userEvent.setup();
    render(<TokenUsageChart sessionContext={sessionContext} apiUrl={apiUrl} height={300} />);
    expect(screen.getByText("Loading…")).toBeInTheDocument();
    // the y axis's ticks are formatted numbers.
    expect(await screen.findByText("10,000")).toBeInTheDocument();
    expect(screen.queryByText("Loading…")).not.toBeInTheDocument();

    await user.selectOptions(screen.getByRole("combobox"), "7_days");
    await vi.waitFor(() => expect(requested).toEqual(["1_hour", "7_days"]));
  });

  it.each([
    [HttpResponse.json({ error: "Service unavailable" }, { status: 503 }), "(503): Service unavailable"],
    [new HttpResponse("not json", { status: 500, statusText: "Server Error" }), "(500): Server Error"],
  ])("shows why the usage failed to load", async (response, message) => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    server.use(http.post(`${apiUrl}:periodicity/`, () => response.clone()));
    render(<TokenUsageChart sessionContext={sessionContext} apiUrl={apiUrl} />);
    expect(await screen.findByText(`Failed to fetch tokenUsageData ${message}`)).toBeInTheDocument();
  });
});

/* eslint-disable testing-library/no-container, testing-library/no-node-access -- Recharts draws its lines and bars as SVG shapes, without roles or text. */
import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { budgetSeries } from "@/mocks/fixtures";

import BudgetChart from "@/components/BudgetVsActual/BudgetChart";

vi.mock("recharts", async (importOriginal) => (await import("@test/recharts")).withFixedSize(await importOriginal()));

const [costSeries, tokenSeries] = budgetSeries;

describe("BudgetChart", () => {
  it("labels a cost budget's axis in dollars, with its limit", () => {
    const { container } = render(
      <BudgetChart series={costSeries.series} unit="cost" period="month" periodicLimit={100} />,
    );
    expect(screen.getAllByText(/^\$\d/).length).toBeGreaterThan(0);
    expect(screen.getByText("Apr 2026")).toBeInTheDocument();
    expect(container.querySelector(".recharts-line")).toBeInTheDocument();
  });

  it("labels a token budget's axis in tokens, without a limit line when it has none", () => {
    const { container } = render(
      <BudgetChart series={tokenSeries.series} unit="tokens" period="day" periodicLimit={0} />,
    );
    expect(screen.queryAllByText(/^\$/)).toHaveLength(0);
    expect(screen.getAllByText(/^\d{1,3}(,\d{3})*$/).length).toBeGreaterThan(0);
    expect(container.querySelector(".recharts-line")).not.toBeInTheDocument();
  });

  it("marks the periods that reach the limit", async () => {
    const series = costSeries.series.map((row, i) => ({ ...row, actual: i === 0 ? 150 : 10 }));
    const { container } = render(<BudgetChart series={series} unit="cost" period="week" periodicLimit={100} />);
    await waitFor(() => expect(container.querySelectorAll(".recharts-bar-rectangle path")).toHaveLength(3));
    const fills = [...container.querySelectorAll(".recharts-bar-rectangle path")].map((bar) =>
      bar.getAttribute("fill"),
    );
    expect(fills).toEqual(["#F8285A", "#17C653", "#17C653"]);
  });
});

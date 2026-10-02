/** Types and formatting of the budget versus actual chart. */

export type BudgetUnit = "cost" | "tokens";
export type BudgetPeriod = "hour" | "day" | "week" | "month";

export interface BudgetSeriesRow {
  period_start: string;
  period_end: string;
  budget: number;
  actual: number;
  total_tokens: number;
  total_cost: number;
}

export interface BudgetChartProps {
  series: BudgetSeriesRow[];
  unit: BudgetUnit;
  period: BudgetPeriod;
  periodicLimit: number;
  height?: number;
}

export function formatAmount(value: number, unit: BudgetUnit): string {
  if (unit === "tokens") return `${Math.round(value).toLocaleString()} tokens`;
  return value.toLocaleString(undefined, { style: "currency", currency: "USD" });
}

export function formatPeriod(iso: string, period: BudgetPeriod): string {
  const date = new Date(iso);
  switch (period) {
    case "hour":
      return date.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
    case "day":
      return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
    case "week":
      return `Week of ${date.toLocaleDateString(undefined, { month: "short", day: "numeric" })}`;
    default:
      return date.toLocaleDateString(undefined, { month: "short", year: "numeric" });
  }
}

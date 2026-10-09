import type { BudgetPeriod, BudgetSeriesRow, BudgetUnit } from "@/components/BudgetVsActual/format";

/** The status of a budget attached to a resource, from /dashboard/api/budgets/. */
export interface BudgetStatus {
  budget: string;
  resource_locator: string;
  is_active: boolean;
  unit: BudgetUnit;
  period: BudgetPeriod;
  action: "block" | "warn";
  start_date: string;
  expires_at: string | null;
  is_expired: boolean;
  period_start: string;
  period_end: string;
  periodic_limit: number;
  periodic_actual: number;
  periodic_percent: number | null;
  absolute_limit: number;
  absolute_actual: number;
  absolute_percent: number | null;
  is_locked: boolean;
  lock_reason: string | null;
}

/** One budget of a resource, with its series, from /dashboard/api/budgets/<locator>/series/. */
export interface BudgetSeries {
  status: BudgetStatus;
  series: BudgetSeriesRow[];
}

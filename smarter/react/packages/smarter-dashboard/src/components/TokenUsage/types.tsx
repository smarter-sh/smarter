import type { SessionContext } from "@smarter/common";

/** The period of each point: Charges are aggregated by the hour, so an hour is the smallest. */
export type TokenUsagePeriod = "hour" | "day" | "month";

/** The tokens and cost of one period, from smarter.apps.dashboard.views.views.api.charges.TokenUsagePoint. */
export interface TokenUsagePoint {
  period_start: string;
  records: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  total_cost: number;
}

/** The points of one window, oldest first, from smarter.apps.dashboard.views.views.api.charges.TokenUsageSeries. */
export interface TokenUsageSeries {
  periodicity: string;
  period: TokenUsagePeriod;
  points: TokenUsagePoint[];
}

export interface TokenUsageChartProps {
  sessionContext: SessionContext;
  apiUrl: string;
  height?: number;
}

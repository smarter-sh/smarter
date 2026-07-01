import type { AreaSeries, LineSeries, TokenUsagePoint } from "./types";
// -----------------------------------------------------------------------------
// Example
// -----------------------------------------------------------------------------

export const data: TokenUsagePoint[] = [
  {
    timestamp: "09:00",
    requestTokens: 12000,
    completionTokens: 7000,
    budgetTokens: 30000,
    totalTokens: 19000,
    remainingTokens: 11000,
    utilization: 0.633,
  },
  {
    timestamp: "10:00",
    requestTokens: 18000,
    completionTokens: 9000,
    budgetTokens: 60000,
    totalTokens: 27000,
    remainingTokens: 33000,
    utilization: 0.45,
  },
  {
    timestamp: "11:00",
    requestTokens: 22000,
    completionTokens: 11000,
    budgetTokens: 90000,
    totalTokens: 33000,
    remainingTokens: 57000,
    utilization: 0.367,
  },
];

export const areas: AreaSeries[] = [
  {
    key: "requestTokens",
    label: "Request",
    color: "#3b82f6",
  },
  {
    key: "completionTokens",
    label: "Completion",
    color: "#10b981",
  },
];

export const lines: LineSeries[] = [
  {
    key: "budgetTokens",
    label: "Budget",
    color: "#111827",
  },
];

// Usage:
//
// <TokenUsageChart
//     data={data}
//     areas={areas}
//     lines={lines}
// />

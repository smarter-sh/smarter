import type { SessionContext } from "@smarter/common";

export interface TokenUsageInterface {
  timestamp: string;

  requestTokens: number;
  completionTokens: number;
  budgetTokens: number;

  totalTokens: number;
  remainingTokens: number;
  utilization: number;
}

export interface AreaSeries {
  key: keyof TokenUsageInterface;
  label: string;
  color: string;
}

export interface LineSeries {
  key: keyof TokenUsageInterface;
  label: string;
  color: string;
}

export interface TokenUsageChartProps {
  sessionContext: SessionContext;
  apiUrl: string;
  height?: number;
}

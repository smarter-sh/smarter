export interface TokenUsagePoint {
  timestamp: string;

  requestTokens: number;
  completionTokens: number;
  budgetTokens: number;

  totalTokens: number;
  remainingTokens: number;
  utilization: number;
}

export interface AreaSeries {
  key: keyof TokenUsagePoint;
  label: string;
  color: string;
}

export interface LineSeries {
  key: keyof TokenUsagePoint;
  label: string;
  color: string;
}

export interface TokenUsageChartProps {
  data: TokenUsagePoint[];
  areas: AreaSeries[];
  lines: LineSeries[];
  height?: number;
}

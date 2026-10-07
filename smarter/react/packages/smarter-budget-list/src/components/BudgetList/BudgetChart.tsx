/**
 * BudgetChart
 *
 * A budget versus actual chart: a bar of the actual spending of each billing period, red when
 * it reached the budget, and the budget's periodic limit as a line.
 *
 * The data is a series from the Smarter dashboard API, /dashboard/api/budgets/<locator>/series/.
 */
import {
  Bar,
  CartesianGrid,
  Cell,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { formatAmount, formatPeriod } from "./format";
import type { BudgetChartProps } from "./format";

const ACTUAL_COLOR = "#17C653";
const OVER_COLOR = "#F8285A";
const BUDGET_COLOR = "#111827";

export default function BudgetChart({ series, unit, period, periodicLimit, height = 320 }: BudgetChartProps) {
  const data = series.map((row) => ({ ...row, label: formatPeriod(row.period_start, period) }));
  const tick = (value: number) => (unit === "tokens" ? value.toLocaleString() : `$${value.toLocaleString()}`);
  return (
    <ResponsiveContainer width="100%" height={height}>
      <ComposedChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="label" />
        <YAxis tickFormatter={tick} />
        <Tooltip formatter={(value) => (typeof value === "number" ? formatAmount(value, unit) : (value ?? ""))} />
        <Legend />
        <Bar dataKey="actual" name="Actual" fill={ACTUAL_COLOR}>
          {data.map((row) => (
            <Cell
              key={row.period_start}
              fill={periodicLimit > 0 && row.actual >= periodicLimit ? OVER_COLOR : ACTUAL_COLOR}
            />
          ))}
        </Bar>
        {periodicLimit > 0 && (
          <Line type="stepAfter" dataKey="budget" name="Budget" stroke={BUDGET_COLOR} strokeWidth={3} dot={false} />
        )}
      </ComposedChart>
    </ResponsiveContainer>
  );
}

import { ResponsiveContainer, AreaChart, Area, Line, CartesianGrid, XAxis, YAxis, Tooltip, Legend } from "recharts";
import type { TokenUsageChartProps } from "./types";

export function TokenUsageChart({ data, areas, lines, height = 400 }: TokenUsageChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="timestamp" />
        <YAxis tickFormatter={(value: number) => value.toLocaleString()} />

        <Tooltip
          formatter={(value) => {
            if (typeof value === "number") {
              return value.toLocaleString();
            }

            return value ?? "";
          }}
        />

        <Legend />

        {areas.map((series) => (
          <Area
            key={String(series.key)}
            type="monotone"
            dataKey={series.key}
            name={series.label}
            stackId="usage"
            fill={series.color}
            stroke={series.color}
          />
        ))}

        {lines.map((series) => (
          <Line
            key={String(series.key)}
            type="monotone"
            dataKey={series.key}
            name={series.label}
            stroke={series.color}
            strokeWidth={3}
            dot={false}
            activeDot={{ r: 5 }}
          />
        ))}
      </AreaChart>
    </ResponsiveContainer>
  );
}

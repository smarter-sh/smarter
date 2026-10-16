import { useEffect, useState } from "react";
import { fetchDjangoUrl, gettext, interpolate } from "@smarter/common";
import { ResponsiveContainer, AreaChart, Area, Line, CartesianGrid, XAxis, YAxis, Tooltip, Legend } from "recharts";
import type { AreaSeries, LineSeries, TokenUsageChartProps, TokenUsageInterface } from "@/components/TokenUsage/types";
import { loggerPrefix } from "@/const";

const areas: AreaSeries[] = [
  {
    key: "requestTokens",
    label: gettext("Request"),
    color: "#ff5733",
  },
  {
    key: "completionTokens",
    label: gettext("Completion"),
    color: "#17C653",
  },
];

const lines: LineSeries[] = [
  {
    key: "budgetTokens",
    label: gettext("Limit"),
    color: "#111827",
  },
];

const PERIODICITY_OPTIONS = [
  { label: gettext("Hour"), value: "1_hour" },
  { label: gettext("Half Day"), value: "12_hours" },
  { label: gettext("Day"), value: "24_hours" },
  { label: gettext("Week"), value: "7_days" },
  { label: gettext("Month"), value: "1_month" },
  { label: gettext("Year"), value: "1_year" },
];

type DropdownProps = {
  value: string;
  onChange: (value: string) => void;
};

function ChargesPeriodicityDropdown({ value, onChange }: DropdownProps) {
  return (
    <select value={value} onChange={(e) => onChange(e.target.value)}>
      {PERIODICITY_OPTIONS.map((option) => (
        <option value={option.value} key={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  );
}

export default function TokenUsageChart({ sessionContext, apiUrl, height = 400 }: TokenUsageChartProps) {
  const [tokenUsageData, setTokenUsageData] = useState<TokenUsageInterface[]>([]);
  const [periodicity, setPeriodicity] = useState("1_hour");
  const [errMessage, setErrMessage] = useState<string>("");
  // loading until the first fetch completes, and again whenever the periodicity changes.
  const [isLoading, setIsLoading] = useState(true);

  const handlePeriodicityChange = (value: string) => {
    setPeriodicity(value);
    setIsLoading(true);
    setErrMessage("");
  };

  useEffect(() => {
    const url = `${apiUrl}${encodeURIComponent(periodicity)}/`;

    fetchDjangoUrl(sessionContext, url, JSON.stringify({}))
      .then((response) => {
        if (!response.ok) {
          return response
            .json()
            .catch(() => null)
            .then((errorData) => {
              const errorMessage = errorData?.error || response.statusText;
              throw new Error(
                interpolate(gettext("Failed to fetch tokenUsageData (%(status)s): %(error)s"), {
                  status: response.status,
                  error: errorMessage,
                }),
              );
            });
        }
        return response.json();
      })
      .then((data: TokenUsageInterface[]) => {
        setTokenUsageData(data);
        console.debug(loggerPrefix, "Successfully fetched tokenUsageData:", data);
      })
      .catch((error: Error) => {
        console.error(loggerPrefix, "Error fetching tokenUsageData:", error);
        setErrMessage(error.message);
      })
      .finally(() => {
        setIsLoading(false);
      });

    return () => {};
  }, [sessionContext, apiUrl, periodicity]);

  return (
    <div>
      <div style={{ marginBottom: "1rem" }}>
        <ChargesPeriodicityDropdown value={periodicity} onChange={handlePeriodicityChange} />
      </div>

      {errMessage && <div style={{ color: "#b91c1c", marginBottom: "0.5rem", fontSize: "0.9rem" }}>{errMessage}</div>}

      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={tokenUsageData}>
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

      {isLoading && <div style={{ marginTop: "0.5rem", fontSize: "0.85rem", opacity: 0.6 }}>{gettext("Loading…")}</div>}
    </div>
  );
}

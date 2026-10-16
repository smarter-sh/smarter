/**
 * ResourceChart
 *
 * Loads a resource's budget versus actual series, and charts it. Loaded in its own chunk,
 * with recharts.
 */
import { useEffect, useState } from "react";
import { fetchDjangoUrl, gettext, interpolate } from "@smarter/common";
import type { SessionContext } from "@smarter/common";

import BudgetChart from "@/components/BudgetList/BudgetChart";
import type { BudgetSeriesRow } from "@/components/BudgetList/format";
import type { BudgetResourceStatus } from "@/lib/Types";
import { loggerPrefix } from "@/lib/const";

const PERIODS = 12;

type SeriesResponse = { status: { budget: string }; series: BudgetSeriesRow[] }[];

export default function ResourceChart({
  sessionContext,
  status,
}: {
  sessionContext: SessionContext;
  status: BudgetResourceStatus;
}) {
  const [series, setSeries] = useState<BudgetSeriesRow[] | null>(null);
  const [errMessage, setErrMessage] = useState("");

  useEffect(() => {
    fetchDjangoUrl(sessionContext, `${status.seriesUrl}?periods=${PERIODS}`, JSON.stringify({}))
      .then(async (response) => {
        if (!response.ok)
          throw new Error(
            interpolate(gettext("Failed to load the budget series (%(status)s)."), { status: response.status }),
          );
        const data = (await response.json()) as SeriesResponse;
        setSeries(data.find((s) => s.status.budget === status.budget)?.series ?? []);
      })
      .catch((error: Error) => {
        console.error(loggerPrefix, "Error loading budget series:", error);
        setErrMessage(error.message);
      });
  }, [sessionContext, status]);

  if (errMessage) return <div className="text-danger fs-7">{errMessage}</div>;
  if (series === null) return <div className="text-muted fs-7">{gettext("Loading…")}</div>;
  return (
    <BudgetChart
      series={series}
      unit={status.unit}
      period={status.period}
      periodicLimit={status.periodicLimit}
      height={260}
    />
  );
}

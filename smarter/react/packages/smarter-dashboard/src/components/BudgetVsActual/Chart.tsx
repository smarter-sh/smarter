/**
 * BudgetVsActualChart
 *
 * Lets the user choose one of the budgets that apply to them, or to the resources they may see,
 * and charts its budget versus the actual spending of the last 12 billing periods.
 */
import { useEffect, useMemo, useState } from "react";
import { fetchDjangoUrl } from "@smarter/common";
import type { SessionContext } from "@smarter/common";

import BudgetChart from "@/components/BudgetVsActual/BudgetChart";
import { formatAmount } from "@/components/BudgetVsActual/format";
import type { BudgetSeries, BudgetStatus } from "@/components/BudgetVsActual/types";
import { loggerPrefix } from "@/const";

const PERIODS = 12;

const keyOf = (status: BudgetStatus) => `${status.budget}|${status.resource_locator}`;

async function postJson<T>(sessionContext: SessionContext, url: string): Promise<T> {
  const response = await fetchDjangoUrl(sessionContext, url, JSON.stringify({}));
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(`(${response.status}) ${body?.error || response.statusText}`);
  }
  return response.json() as Promise<T>;
}

function Usage({
  label,
  actual,
  limit,
  percent,
  status,
}: {
  label: string;
  actual: number;
  limit: number;
  percent: number | null;
  status: BudgetStatus;
}) {
  if (!limit) return null;
  const over = percent !== null && percent >= 100;
  return (
    <span className={`badge ${over ? "badge-light-danger" : "badge-light-success"} me-2 fs-7`}>
      {label}: {formatAmount(actual, status.unit)} of {formatAmount(limit, status.unit)}
      {percent !== null ? ` (${percent}%)` : ""}
    </span>
  );
}

export default function BudgetVsActualChart({
  sessionContext,
  apiUrl,
}: {
  sessionContext: SessionContext;
  apiUrl: string;
}) {
  const [statuses, setStatuses] = useState<BudgetStatus[] | null>(null);
  const [selected, setSelected] = useState<string>("");
  const [series, setSeries] = useState<BudgetSeries | null>(null);
  const [errMessage, setErrMessage] = useState<string>("");

  useEffect(() => {
    postJson<BudgetStatus[]>(sessionContext, apiUrl)
      .then((data) => {
        setStatuses(data);
        if (data.length > 0) setSelected(keyOf(data[0]));
      })
      .catch((error: Error) => {
        console.error(loggerPrefix, "Error fetching budgets:", error);
        setErrMessage(error.message);
      });
  }, [sessionContext, apiUrl]);

  const status = useMemo(() => statuses?.find((s) => keyOf(s) === selected) ?? null, [statuses, selected]);

  useEffect(() => {
    if (!status) return;
    const base = apiUrl.endsWith("/") ? apiUrl : `${apiUrl}/`;
    const url = `${base}${encodeURIComponent(status.resource_locator)}/series/?periods=${PERIODS}`;
    postJson<BudgetSeries[]>(sessionContext, url)
      .then((data) => setSeries(data.find((s) => s.status.budget === status.budget) ?? null))
      .catch((error: Error) => {
        console.error(loggerPrefix, "Error fetching budget series:", error);
        setErrMessage(error.message);
      });
  }, [sessionContext, apiUrl, status]);

  if (statuses === null && !errMessage) return <div style={{ fontSize: "0.85rem", opacity: 0.6 }}>Loading…</div>;
  if (statuses !== null && statuses.length === 0) {
    return <div className="text-muted">No budgets apply to you, or to your resources.</div>;
  }

  return (
    <div>
      {errMessage && <div style={{ color: "#b91c1c", marginBottom: "0.5rem", fontSize: "0.9rem" }}>{errMessage}</div>}
      {statuses && (
        <div className="d-flex flex-wrap align-items-center mb-4 gap-2">
          <select
            className="form-select form-select-sm w-auto"
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
          >
            {statuses.map((s) => (
              <option key={keyOf(s)} value={keyOf(s)}>
                {s.budget} — {s.resource_locator}
              </option>
            ))}
          </select>
          {status && (
            <>
              <Usage
                label={`This ${status.period}`}
                actual={status.periodic_actual}
                limit={status.periodic_limit}
                percent={status.periodic_percent}
                status={status}
              />
              <Usage
                label="Total"
                actual={status.absolute_actual}
                limit={status.absolute_limit}
                percent={status.absolute_percent}
                status={status}
              />
              {status.is_locked && (
                <span className="badge badge-danger fs-7" title={status.lock_reason ?? ""}>
                  Blocked
                </span>
              )}
              {status.is_expired && <span className="badge badge-light fs-7">Ended</span>}
            </>
          )}
        </div>
      )}
      {status && series && (
        <BudgetChart
          series={series.series}
          unit={status.unit}
          period={status.period}
          periodicLimit={status.periodic_limit}
        />
      )}
    </div>
  );
}

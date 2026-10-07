/**
 * BudgetList
 *
 * Lists the budgets that the user may see. Each budget expands to the resources it is attached
 * to, with their budget versus actual spending, and a chart of the last 12 billing periods.
 * Superusers may delete a budget. Budgets are created and changed with Budget manifests.
 */
import React, { lazy, Suspense, useCallback, useEffect, useState } from "react";
import { Loading, actionUrl, fetchDjangoUrl, formatDateTime } from "@smarter/common";
import type { SessionContext } from "@smarter/common";

import { formatAmount } from "./format";
import type { Budget, BudgetListResponse, BudgetResourceStatus } from "@/lib/Types";
import { loggerPrefix } from "@/lib/const";

import "./styles.css";

// recharts is a large dependency, so the chart is loaded in its own chunk.
const ResourceChart = lazy(() => import("./ResourceChart"));

function resourceLabel(status: BudgetResourceStatus): string {
  const { kind, name, recordLocator } = status.resource;
  return kind && name ? `${kind} ${name}` : (recordLocator ?? status.resourceLocator);
}

function Usage({
  actual,
  limit,
  percent,
  unit,
}: {
  actual: number;
  limit: number;
  percent: number | null;
  unit: BudgetResourceStatus["unit"];
}) {
  if (!limit) return <span className="text-muted">No limit</span>;
  const pct = Math.min(percent ?? 0, 100);
  const color = pct >= 100 ? "bg-danger" : pct >= 80 ? "bg-warning" : "bg-success";
  return (
    <div className="budget-usage">
      <div className="fs-8 mb-1">
        {formatAmount(actual, unit)} of {formatAmount(limit, unit)} {percent !== null && `(${percent}%)`}
      </div>
      <div className="progress h-6px">
        <div className={`progress-bar ${color}`} role="progressbar" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function ResourceStatusRow({
  sessionContext,
  status,
}: {
  sessionContext: SessionContext;
  status: BudgetResourceStatus;
}) {
  const [showChart, setShowChart] = useState(false);
  return (
    <>
      <tr>
        <td>
          <span className="fw-semibold">{resourceLabel(status)}</span>
          <div className="text-muted fs-8">{status.resourceLocator}</div>
        </td>
        <td>
          <Usage
            actual={status.periodicActual}
            limit={status.periodicLimit}
            percent={status.periodicPercent}
            unit={status.unit}
          />
        </td>
        <td>
          <Usage
            actual={status.absoluteActual}
            limit={status.absoluteLimit}
            percent={status.absolutePercent}
            unit={status.unit}
          />
        </td>
        <td>
          {status.isExpired ? (
            <span className="badge badge-light">Ended</span>
          ) : status.isLocked ? (
            <span className="badge badge-danger" title={status.lockReason ?? ""}>
              Blocked
            </span>
          ) : (
            <span className="badge badge-light-success">Within budget</span>
          )}
        </td>
        <td className="text-end">
          <button type="button" className="btn btn-sm btn-light" onClick={() => setShowChart(!showChart)}>
            <i className="bi bi-bar-chart" /> {showChart ? "Hide" : "Chart"}
          </button>
        </td>
      </tr>
      {showChart && (
        <tr>
          <td colSpan={5}>
            <Suspense fallback={<Loading />}>
              <ResourceChart sessionContext={sessionContext} status={status} />
            </Suspense>
          </td>
        </tr>
      )}
    </>
  );
}

const BudgetRow = React.memo(function BudgetRow({
  sessionContext,
  budget,
  isSuperuser,
  onDelete,
}: {
  sessionContext: SessionContext;
  budget: Budget;
  isSuperuser: boolean;
  onDelete: (budget: Budget) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const limit = (value: string, suffix: string) =>
    Number(value) > 0 ? `${formatAmount(Number(value), budget.unit)}${suffix}` : null;
  const limits = [limit(budget.periodicLimit, ` / ${budget.period}`), limit(budget.absoluteLimit, " total")].filter(
    Boolean,
  );
  return (
    <>
      <tr className={budget.locked > 0 ? "budget-row-locked" : ""}>
        <td>
          <button
            type="button"
            className="btn btn-icon btn-sm"
            aria-label="Show resources"
            onClick={() => setExpanded(!expanded)}
          >
            <i className={`bi ${expanded ? "bi-chevron-down" : "bi-chevron-right"}`} />
          </button>
          <a href={budget.manifestUrl}>{budget.name}</a>
          <div className="text-muted fs-8">{budget.description}</div>
        </td>
        <td>{limits.length ? limits.join(", ") : "No limit"}</td>
        <td>{budget.action === "block" ? "Block" : "Warn"}</td>
        <td>{budget.resources}</td>
        <td>
          {budget.locked > 0 ? (
            <span className="badge badge-danger">{budget.locked} blocked</span>
          ) : (
            <span className="text-muted">None</span>
          )}
        </td>
        <td className="d-none d-lg-table-cell">{formatDateTime(budget.updatedAt, "relative", budget.createdAt)}</td>
        <td className="text-end">
          {isSuperuser && (
            <button type="button" className="btn btn-sm btn-light-danger" onClick={() => onDelete(budget)}>
              <i className="bi bi-trash" /> Delete
            </button>
          )}
        </td>
      </tr>
      {expanded && (
        <tr className="budget-resources">
          <td colSpan={7}>
            {budget.resourceStatus.length === 0 ? (
              <div className="text-muted p-3">This budget is not attached to any resource that you may see.</div>
            ) : (
              <table className="table table-sm align-middle mb-0">
                <thead>
                  <tr>
                    <th>Resource</th>
                    <th>This {budget.period}</th>
                    <th>Total</th>
                    <th>Status</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {budget.resourceStatus.map((status) => (
                    <ResourceStatusRow key={status.resourceLocator} sessionContext={sessionContext} status={status} />
                  ))}
                </tbody>
              </table>
            )}
          </td>
        </tr>
      )}
    </>
  );
});

export default function BudgetList({ sessionContext }: { sessionContext: SessionContext }) {
  const [data, setData] = useState<BudgetListResponse | null>(null);
  const [errMessage, setErrMessage] = useState("");

  const load = useCallback(() => {
    fetchDjangoUrl(sessionContext, sessionContext.ApiUrl, JSON.stringify({}))
      .then(async (response) => {
        if (!response.ok) throw new Error(`Failed to load budgets (${response.status}).`);
        setData((await response.json()) as BudgetListResponse);
        setErrMessage("");
      })
      .catch((error: Error) => {
        console.error(loggerPrefix, "Error loading budgets:", error);
        setErrMessage(error.message);
      });
  }, [sessionContext]);

  useEffect(() => {
    load();
  }, [load]);

  const onDelete = useCallback(
    (budget: Budget) => {
      if (
        !window.confirm(
          `Delete the budget ${budget.name}? It will no longer be enforced on its ${budget.resources} resources.`,
        )
      )
        return;
      fetchDjangoUrl(sessionContext, actionUrl(sessionContext, `delete/${budget.id}/`), JSON.stringify({}))
        .then(async (response) => {
          if (!response.ok) {
            const body = await response.json().catch(() => null);
            throw new Error(body?.error || `Failed to delete the budget (${response.status}).`);
          }
          load();
        })
        .catch((error: Error) => setErrMessage(error.message));
    },
    [sessionContext, load],
  );

  return (
    <div className="card mt-5">
      <div className="card-body">
        {errMessage && (
          <div className="alert alert-danger" role="alert">
            {errMessage}
          </div>
        )}
        {data === null && !errMessage && <Loading />}
        {data && data.objects.length === 0 && (
          <div className="text-muted p-4">
            {data.isSuperuser
              ? "There are no budgets. Create one with a Budget manifest: smarter apply -f budget.yaml"
              : "No budgets apply to you, or to your resources."}
          </div>
        )}
        {data && data.objects.length > 0 && (
          <div className="table-responsive">
            <table className="table table-striped table-hover align-middle border">
              <thead className="table-light">
                <tr>
                  <th>Name</th>
                  <th>Limits</th>
                  <th>Action</th>
                  <th>Resources</th>
                  <th>Blocked</th>
                  <th className="d-none d-lg-table-cell">Updated</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {data.objects.map((budget) => (
                  <BudgetRow
                    key={budget.id}
                    sessionContext={sessionContext}
                    budget={budget}
                    isSuperuser={data.isSuperuser}
                    onDelete={onDelete}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

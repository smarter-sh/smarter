/**
 * BudgetAlerts dashboard widget.
 *
 * This component renders a banner at the top of the dashboard for each budget
 * that is locked, or whose spending has reached ALERT_PERCENT of its periodic
 * or absolute limit. It renders nothing when no budget needs attention.
 *
 * :param sessionContext: Session context used for authenticated requests.
 * :type sessionContext: SessionContext
 * :param apiUrl: The budgets endpoint, also used by the BudgetVsActual widget.
 * :type apiUrl: str
 *
 * :returns: A JSX element containing the budget alert banners, or null.
 * :rtype: JSX.Element | null
 *
 * :example:
 *
 *     <BudgetAlerts sessionContext={sessionContext} apiUrl="/dashboard/api/budgets/" />
 */
import type { ReactNode } from "react";
import type { SessionContext } from "@smarter/common";

import useDashboardApi from "@/hooks/useDashboardApi";
import { formatAmount } from "@/components/BudgetVsActual/format";
import type { BudgetStatus } from "@/components/BudgetVsActual/types";
import { gettext, interpolateNodes } from "@smarter/common";

export const ALERT_PERCENT = 80;

/** The message for a budget that has spent most of its periodic limit, one per period. */
const periodicMessage = (period: BudgetStatus["period"]): string => {
  switch (period) {
    case "hour":
      return gettext(
        "Budget %(budget)s on %(resource)s has spent %(percent)s of its hourly limit (%(actual)s of %(limit)s).",
      );
    case "day":
      return gettext(
        "Budget %(budget)s on %(resource)s has spent %(percent)s of its daily limit (%(actual)s of %(limit)s).",
      );
    case "week":
      return gettext(
        "Budget %(budget)s on %(resource)s has spent %(percent)s of its weekly limit (%(actual)s of %(limit)s).",
      );
    default:
      return gettext(
        "Budget %(budget)s on %(resource)s has spent %(percent)s of its monthly limit (%(actual)s of %(limit)s).",
      );
  }
};

interface BudgetAlertsProps {
  sessionContext: SessionContext;
  apiUrl: string;
}

/** The highest percent of a budget's limits that has been spent, or null if it has no limits. */
function spentPercent(status: BudgetStatus): number | null {
  const percents = [status.periodic_percent, status.absolute_percent].filter((p): p is number => p !== null);
  return percents.length ? Math.max(...percents) : null;
}

function needsAttention(status: BudgetStatus): boolean {
  if (!status.is_active || status.is_expired) return false;
  const percent = spentPercent(status);
  return status.is_locked || (percent !== null && percent >= ALERT_PERCENT);
}

/** The alert's sentence, with the budget's and the resource's names in bold. */
function alertMessage(status: BudgetStatus): ReactNode {
  const names = {
    budget: <span className="fw-bold">{status.budget}</span>,
    resource: <span className="fw-bold">{status.resource_locator}</span>,
  };
  if (status.is_locked) {
    return status.lock_reason
      ? interpolateNodes(gettext("Budget %(budget)s on %(resource)s is locked: %(reason)s"), {
          ...names,
          reason: status.lock_reason,
        })
      : interpolateNodes(gettext("Budget %(budget)s on %(resource)s is locked."), names);
  }
  const periodic = status.periodic_percent ?? 0;
  const absolute = status.absolute_percent ?? 0;
  if (periodic >= absolute) {
    return interpolateNodes(periodicMessage(status.period), {
      ...names,
      percent: `${periodic}%`,
      actual: formatAmount(status.periodic_actual, status.unit),
      limit: formatAmount(status.periodic_limit, status.unit),
    });
  }
  return interpolateNodes(
    gettext("Budget %(budget)s on %(resource)s has spent %(percent)s of its total limit (%(actual)s of %(limit)s)."),
    {
      ...names,
      percent: `${absolute}%`,
      actual: formatAmount(status.absolute_actual, status.unit),
      limit: formatAmount(status.absolute_limit, status.unit),
    },
  );
}

function BudgetAlerts({ sessionContext, apiUrl }: BudgetAlertsProps) {
  const { data } = useDashboardApi<BudgetStatus[]>(sessionContext, apiUrl);
  const alerts = (data ?? []).filter(needsAttention);
  if (alerts.length === 0) return null;

  return (
    <section id="budget-alerts" aria-label={gettext("Budget Alerts")} className="row g-5 g-xl-10 mt-3">
      <div className="col-12">
        {alerts.map((status) => {
          const danger = status.is_locked || (spentPercent(status) ?? 0) >= 100;
          return (
            <div
              key={`${status.budget}|${status.resource_locator}`}
              role="alert"
              className={`alert ${danger ? "alert-danger" : "alert-warning"} d-flex align-items-center p-4 mb-3`}
            >
              <i
                className={`ki-outline ki-notification-bing fs-2x me-4 ${danger ? "text-danger" : "text-warning"}`}
              ></i>
              <div className="fs-6">{alertMessage(status)}</div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

export default BudgetAlerts;

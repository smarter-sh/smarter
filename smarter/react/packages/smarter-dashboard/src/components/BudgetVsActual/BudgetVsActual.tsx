import { lazy, Suspense } from "react";
import type { SessionContext } from "@smarter/common";

import "@/components/BudgetVsActual/styles.css";

// recharts is a large dependency, so the chart is loaded in its own chunk.
const BudgetVsActualChart = lazy(() => import("@/components/BudgetVsActual/Chart"));

interface BudgetVsActualProps {
  sessionContext: SessionContext;
  apiUrl: string;
}

/** A dashboard card with the budget versus actual chart of the budgets that apply to the user. */
function BudgetVsActual({ sessionContext, apiUrl }: BudgetVsActualProps) {
  return (
    <div id="budget-vs-actual" aria-label="Budget vs Actual" className="col-xl-12 mb-5 mb-xl-10">
      <div className="card border-transparent" data-bs-theme="light">
        <div className="card-body d-flex flex-column ps-xl-15 h-100">
          <h6 className="text-muted opacity-75-hover w-100 my-4 fs-3 fw-bold">Budget vs Actual</h6>
          <Suspense fallback={null}>
            <BudgetVsActualChart sessionContext={sessionContext} apiUrl={apiUrl} />
          </Suspense>
        </div>
      </div>
    </div>
  );
}

export default BudgetVsActual;

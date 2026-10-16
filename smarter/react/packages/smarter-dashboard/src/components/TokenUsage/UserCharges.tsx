import { lazy, Suspense } from "react";
import type { SessionContext } from "@smarter/common";

import "@/components/TokenUsage/styles.css";
import { gettext } from "@smarter/common";

// recharts is a large dependency and is only needed for this chart, so it's
// loaded in its own chunk instead of bloating the main app bundle.
const TokenUsageChart = lazy(() => import("@/components/TokenUsage/Chart"));

interface UserUsageProps {
  sessionContext: SessionContext;
  apiUrl: string;
  /** The card's grid column classes, so that the dashboard can set its width. */
  className?: string;
}

function UserCharges({ sessionContext, apiUrl, className = "col-xl-12" }: UserUsageProps) {
  console.debug("apiUrl", apiUrl);
  return (
    <>
      <div id="user-usage" aria-label={gettext("User Usage")} className={`${className} mb-5 mb-xl-10`}>
        {/* begin::User Usage */}
        <div className="card border-transparent h-100" data-bs-theme="light">
          {/* begin::Header */}
          <div className="card-header border-0 pt-5">
            <h3 className="card-title align-items-start flex-column">
              <span className="card-label fw-bold text-gray-900">{gettext("Token Usage")}</span>
              <span className="text-muted mt-1 fw-semibold fs-7">
                {gettext("Tokens your LLM requests used, over time")}
              </span>
            </h3>
          </div>
          {/* end::Header */}
          {/* begin::Body */}
          <div className="card-body d-flex flex-column pt-3">
            <Suspense fallback={null}>
              <TokenUsageChart sessionContext={sessionContext} apiUrl={apiUrl} />
            </Suspense>
          </div>
        </div>
      </div>
    </>
  );
}

export default UserCharges;

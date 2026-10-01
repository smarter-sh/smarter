import { lazy, Suspense } from "react";
import type { SessionContext } from "@smarter/common";

import "./styles.css";

// recharts is a large dependency and is only needed for this chart, so it's
// loaded in its own chunk instead of bloating the main app bundle.
const TokenUsageChart = lazy(() => import("./Chart"));

interface UserUsageProps {
  sessionContext: SessionContext,
  apiUrl: string;
}

function UserCharges({ sessionContext, apiUrl }: UserUsageProps) {
  console.debug("apiUrl", apiUrl)
  return (
    <>
      <div id="user-usage" aria-label="User Usage" className="col-xl-12 mb-5 mb-xl-10">
        {/* begin::User Usage */}
        <div className="card border-transparent" data-bs-theme="light">
          {/* begin::Body */}
          <div className="card-body d-flex flex-column ps-xl-15 h-100">
            {/* begin::Title */}
            <h6 className="text-muted  opacity-75-hover w-100 my-4 fs-3 fw-bold">
              Token Usage
            </h6>
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

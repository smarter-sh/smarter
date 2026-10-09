/**
 * QuickActions dashboard widget.
 *
 * This component renders a grid of links to the web console pages that users
 * visit most. The links come from the backend so that console URLs are not
 * hard-coded here.
 *
 * :param sessionContext: Session context used for authenticated requests.
 * :type sessionContext: SessionContext
 * :param apiUrl: Endpoint used to request the quick action links.
 * :type apiUrl: str
 *
 * :returns: A JSX element containing the quick actions card.
 * :rtype: JSX.Element
 *
 * :example:
 *
 *     <QuickActions sessionContext={sessionContext} apiUrl="/dashboard/api/quick-actions/" />
 */
import type { SessionContext } from "@smarter/common";
import { Loading } from "@smarter/common";

import useDashboardApi from "@/hooks/useDashboardApi";
import "@/components/QuickActions/styles.css";

interface QuickAction {
  name: string;
  description: string;
  icon: string;
  url: string;
}

interface QuickActionsProps {
  sessionContext: SessionContext;
  apiUrl: string;
}

function QuickActions({ sessionContext, apiUrl }: QuickActionsProps) {
  const { data, error } = useDashboardApi<QuickAction[]>(sessionContext, apiUrl);

  return (
    <section id="quick-actions" aria-label="Quick Actions" className="col-xl-6 mb-xl-10">
      <div className="card card-flush h-xl-100">
        <div className="card-header pt-5">
          <h4 className="card-title card-label fw-bold text-gray-800">Quick Actions</h4>
        </div>
        <div className="card-body pt-2">
          {error && <div className="text-danger fs-7">Failed to load quick actions: {error}</div>}
          {!data && !error && <Loading />}
          {data && (
            <div className="row g-3">
              {data.map((action) => {
                const external = action.url.startsWith("http");
                return (
                  <div key={action.name} className="col-6">
                    <a
                      href={action.url}
                      target={external ? "_blank" : undefined}
                      rel={external ? "noopener noreferrer" : undefined}
                      className="quick-action d-flex align-items-center bg-gray-100 bg-opacity-70 rounded-2 px-3 py-3 h-100"
                    >
                      <i className={`ki-outline ${action.icon} fs-2 text-primary me-3`}></i>
                      <span>
                        <span className="d-block text-gray-800 fw-bold fs-7">{action.name}</span>
                        <span className="d-block text-gray-500 fs-8">{action.description}</span>
                      </span>
                    </a>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

export default QuickActions;

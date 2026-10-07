/**
 * GettingStarted dashboard widget.
 *
 * This component renders an onboarding checklist for new users: each step,
 * whether the user has done it, and a link to the console page where it is
 * done. It renders nothing once every step is done.
 *
 * :param sessionContext: Session context used for authenticated requests.
 * :type sessionContext: SessionContext
 * :param apiUrl: Endpoint used to request the onboarding steps.
 * :type apiUrl: str
 *
 * :returns: A JSX element containing the checklist card, or null.
 * :rtype: JSX.Element | null
 *
 * :example:
 *
 *     <GettingStarted sessionContext={sessionContext} apiUrl="/dashboard/api/getting-started/" />
 */
import type { SessionContext } from "@smarter/common";

import useDashboardApi from "@/hooks/useDashboardApi";

interface GettingStartedStep {
  name: string;
  description: string;
  done: boolean;
  url: string;
}

interface GettingStartedProps {
  sessionContext: SessionContext;
  apiUrl: string;
}

function GettingStarted({ sessionContext, apiUrl }: GettingStartedProps) {
  const { data } = useDashboardApi<{ steps: GettingStartedStep[] }>(sessionContext, apiUrl);
  const steps = data?.steps ?? [];
  const doneCount = steps.filter((step) => step.done).length;
  if (steps.length === 0 || doneCount === steps.length) return null;

  return (
    <div className="row g-5 g-xl-10">
      <div className="col-xl-12 mb-5 mb-xl-10">
        <section id="getting-started" aria-label="Getting Started" className="card border-transparent">
          <div className="card-header border-0 pt-5">
            <h3 className="card-title align-items-start flex-column">
              <span className="card-label fw-bold text-gray-900">Getting Started</span>
              <span className="text-muted mt-1 fw-semibold fs-7">
                {doneCount} of {steps.length} steps done
              </span>
            </h3>
          </div>
          <div className="card-body pt-3">
            <div className="progress h-6px mb-6">
              <div
                className="progress-bar bg-success"
                role="progressbar"
                style={{ width: `${(doneCount / steps.length) * 100}%` }}
                aria-valuenow={doneCount}
                aria-valuemin={0}
                aria-valuemax={steps.length}
              ></div>
            </div>
            <ol className="list-unstyled row g-4 mb-0">
              {steps.map((step) => (
                <li key={step.name} className="col-md-6 col-xl d-flex align-items-start">
                  <i
                    className={`ki-outline ${step.done ? "ki-check-circle text-success" : "ki-rocket text-gray-400"} fs-2 me-3`}
                    aria-label={step.done ? "done" : "to do"}
                  ></i>
                  <div>
                    <a
                      href={step.url}
                      className={`fw-bold fs-6 ${step.done ? "text-gray-500 text-decoration-line-through" : "text-gray-900 text-hover-primary"}`}
                    >
                      {step.name}
                    </a>
                    <div className="text-gray-600 fs-7">{step.description}</div>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        </section>
      </div>
    </div>
  );
}

export default GettingStarted;

/**
 * GettingStarted dashboard widget.
 *
 * This component renders an onboarding checklist for new users: each step,
 * whether the user has done it, and a link to the console page where it is
 * done. It always shows while any step is left to do. Once every step is
 * done, it remembers the date in the ``smarter_getting_started_done`` browser
 * cookie, and keeps showing, as done, for 90 days after it, then hides itself. Each
 * visit renews the cookie, whose lifetime browsers cap at 400 days, so that
 * the card doesn't come back when the cookie would otherwise expire. If the
 * steps fail to load, it shows the error rather than disappearing.
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
import { useEffect } from "react";
import type { SessionContext } from "@smarter/common";
import { getCookie, setCookie } from "@smarter/common";

import useDashboardApi from "@/hooks/useDashboardApi";
import "@/components/GettingStarted/styles.css";

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

/** How long the card keeps showing after every step is done. */
const SHOW_DONE_FOR_DAYS = 90;

/** The cookie that remembers when every step was first seen done, as an ISO date. */
const DONE_COOKIE_NAME = "smarter_getting_started_done";

const DAY_MS = 24 * 60 * 60 * 1000;
const DONE_COOKIE_LIFETIME_MS = 400 * DAY_MS;

function doneCookie() {
  return { name: DONE_COOKIE_NAME, expiration: DONE_COOKIE_LIFETIME_MS, domain: window.location.hostname, value: null };
}

/** The date every step was first seen done, or null if it never was, or the cookie is unreadable. */
function readDoneSince(): Date | null {
  const value = getCookie(doneCookie(), null);
  const date = value ? new Date(value) : null;
  return date && !Number.isNaN(date.getTime()) ? date : null;
}

/** Whether every step was done long enough ago that the card should hide. */
function doneLongAgo(doneSinceMs: number | null): boolean {
  return doneSinceMs !== null && Date.now() - doneSinceMs > SHOW_DONE_FOR_DAYS * DAY_MS;
}

function GettingStarted({ sessionContext, apiUrl }: GettingStartedProps) {
  const { data, error } = useDashboardApi<{ steps: GettingStartedStep[] }>(sessionContext, apiUrl);
  const steps = data?.steps ?? [];
  const doneCount = steps.filter((step) => step.done).length;
  const allDone = steps.length > 0 && doneCount === steps.length;
  const doneSince = allDone ? readDoneSince() : null;
  const doneSinceMs = doneSince ? doneSince.getTime() : null;

  useEffect(() => {
    if (!allDone) return;
    // record the date on the first visit with every step done, and renew the cookie's expiry on each later one.
    setCookie(doneCookie(), new Date(doneSinceMs ?? Date.now()).toISOString());
  }, [allDone, doneSinceMs]);

  if (error) {
    return (
      <div className="row g-5 g-xl-10">
        <div className="col-xl-12 mb-5 mb-xl-10">
          <section id="getting-started" aria-label="Getting Started" className="card border-transparent">
            <div className="card-body text-danger fs-7">Failed to load the getting started steps: {error}</div>
          </section>
        </div>
      </div>
    );
  }
  if (steps.length === 0) return null;
  if (doneLongAgo(doneSinceMs)) return null;

  return (
    <div className="row g-5 g-xl-10">
      <div className="col-xl-12 mb-5 mb-xl-10">
        <section id="getting-started" aria-label="Getting Started" className="card border-transparent">
          <div className="card-header border-0 pt-5">
            <h3 className="card-title align-items-start flex-column">
              <span className="card-label fw-bold text-gray-900">Getting Started</span>
              <span className="text-muted mt-1 fw-semibold fs-7">
                {allDone ? `All ${steps.length} steps done. Nice work!` : `${doneCount} of ${steps.length} steps done`}
              </span>
            </h3>
          </div>
          <div className="card-body pt-3">
            <div className="progress h-8px mb-6 getting-started-progress">
              <div
                className="progress-bar"
                role="progressbar"
                style={{ width: `${(doneCount / steps.length) * 100}%` }}
                aria-valuenow={doneCount}
                aria-valuemin={0}
                aria-valuemax={steps.length}
              ></div>
            </div>
            <ol className="list-unstyled row g-4 mb-0">
              {steps.map((step, index) => (
                <li key={step.name} className="col-md-6 col-xl d-flex align-items-start">
                  <span
                    className={`getting-started-step me-3 ${step.done ? "getting-started-step-done" : ""}`}
                    aria-label={step.done ? "done" : "to do"}
                  >
                    {step.done ? <i className="ki-outline ki-check fs-3"></i> : index + 1}
                  </span>
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

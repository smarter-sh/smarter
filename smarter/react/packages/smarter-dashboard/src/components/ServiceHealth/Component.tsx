/**
 * ServiceHealth dashboard widget.
 *
 * This component fetches backend service metadata from an API endpoint and
 * renders it in a compact dashboard card: the platform's version and Linux
 * distribution in the header, the runtime versions on one line under it, a ring that shows the
 * share of live checks of the backing services that passed, an overall
 * status, one tile per check, whose tooltip says what it tests, and the
 * build, test and deploy badges of the platform's own repository. The ring
 * and the status are green when every check passes, amber when at least half
 * do, and red otherwise. A narrow card hides the ring, to give the tiles its
 * room. While it loads, and if it can't be loaded, the card shows its own ghost:
 * gray placeholders in the shape of its content, so that the dashboard keeps
 * its layout. The refresh button stays, to try again.
 *
 * Health doesn't change from second to second, so a response is kept for five
 * minutes in localStorage and reused by later page loads, and an open page
 * asks again every five minutes while it's visible. The ring animates only
 * when the score changes, from the score it showed last. The refresh button in
 * the header runs the checks again at once, bypassing the api's cache.
 *
 * :param sessionContext: Session context used for authenticated requests.
 * :type sessionContext: SessionContext
 * :param apiUrl: Endpoint used to request service health and platform version
 *     data.
 * :type apiUrl: str
 *
 * :returns: A JSX element containing the service health card.
 * :rtype: JSX.Element
 *
 * :example:
 *
 *     <ServiceHealth sessionContext={sessionContext} apiUrl="/dashboard/api/service-health/" />
 */
import type { SessionContext } from "@smarter/common";
import { gettext, interpolate, ngettext } from "@smarter/common";

import useDashboardApi from "@/hooks/useDashboardApi";
import HealthRing from "@/components/ServiceHealth/HealthRing";
import type { HealthLevel } from "@/components/ServiceHealth/HealthRing";
import CIStatus from "@/components/ServiceHealth/CIStatus";
import { GhostBody, GhostHeader } from "@/components/ServiceHealth/Ghost";
import "@/components/ServiceHealth/styles.css";

interface ServiceHealthProps {
  sessionContext: SessionContext;
  apiUrl: string;
}

interface HealthCheck {
  name: string;
  healthy: boolean;
}

interface ServiceHealthData {
  linux_distribution: string;
  smarter_version: string;
  django_version: string;
  python_version: string;
  pydantic_version: string;
  drf_version: string;
  repository_url: string;
  health_checks: HealthCheck[];
  health_score: number;
}

interface CheckInfo {
  label: string;
  icon: string;
  description: string;
}

/**
 * What each check that the backend runs is called, its icon, and what it tests, by the name the
 * backend gives it. A check that isn't listed shows its own name, FALLBACK_ICON and no description.
 */
const CHECKS: Record<string, CheckInfo> = {
  Database: {
    label: gettext("Database"),
    icon: "ki-data",
    description: gettext("The database answers a query."),
  },
  Cache: {
    label: gettext("Cache"),
    icon: "ki-disk",
    description: gettext("A value written to the Redis cache can be read back."),
  },
  "Task Broker": {
    label: gettext("Task Broker"),
    icon: "ki-route",
    description: gettext("The Celery task broker, which queues background jobs, accepts a connection."),
  },
  Workers: {
    label: gettext("Workers"),
    icon: "ki-gear",
    description: gettext("At least one Celery worker, which runs background jobs, answers a ping."),
  },
};
const FALLBACK_ICON = "ki-abstract-26";

/**
 * How long a response is reused across page loads, and how often an open page asks again. The checks
 * don't change from second to second, and the api caches them for a minute.
 */
const REFRESH_MS = 5 * 60 * 1000;

/** The Keen color of each health level, for its badge and bullet. */
const LEVEL_COLORS: Record<HealthLevel, string> = {
  healthy: "success",
  degraded: "warning",
  down: "danger",
};

/** Green when every check passes, amber when at least half do, red otherwise. */
function healthLevel(score: number, failing: number): HealthLevel {
  if (failing === 0) return "healthy";
  return score >= 50 ? "degraded" : "down";
}

function StatusBadge({ level, failing, total }: { level: HealthLevel; failing: number; total: number }) {
  const color = LEVEL_COLORS[level];
  return (
    <span className={`badge badge-light-${color} fs-9 fw-bold px-2 py-1 text-nowrap`}>
      <span className={`bullet bullet-dot bg-${color} h-5px w-5px me-1`}></span>
      {failing === 0
        ? gettext("All systems operational")
        : interpolate(
            ngettext("%(failing)s of %(total)s check failing", "%(failing)s of %(total)s checks failing", total),
            { failing, total },
          )}
    </span>
  );
}

function HealthCheckItem({ name, healthy }: HealthCheck) {
  const info = CHECKS[name];
  const label = info?.label ?? name;
  const state = healthy
    ? // Translators: the state of a backend service that answers its health check.
      gettext("Healthy")
    : // Translators: the state of a backend service that fails its health check, i.e. not running.
      gettext("Down");
  return (
    <li
      aria-label={label}
      title={info ? `${label}: ${info.description}` : label}
      className={`service-health-check ${healthy ? "" : "service-health-check-down"}`}
    >
      <i className={`ki-outline ${info?.icon ?? FALLBACK_ICON} fs-2 me-3`} data-testid="check-icon"></i>
      <span className="service-health-check-text">
        <span className="service-health-check-name">{label}</span>
        <span className={`service-health-check-state text-${healthy ? "success" : "danger"}`}>
          <i className={`ki-outline ${healthy ? "ki-check" : "ki-cross"} fs-7 me-1`}></i>
          {state}
        </span>
      </span>
    </li>
  );
}

function RuntimeVersions({ data }: { data: ServiceHealthData }) {
  const versions: [string, string][] = [
    ["Python", data.python_version],
    ["Django", data.django_version],
    ["Pydantic", data.pydantic_version],
    ["DRF", data.drf_version],
  ];
  // one line across the card. A card too narrow for it ends it with an ellipsis, and its tooltip has it all.
  return (
    <ul
      className="service-health-versions"
      aria-label={gettext("Runtime versions")}
      title={versions.map(([name, version]) => `${name} ${version}`).join(" · ")}
    >
      {versions.map(([name, version]) => (
        <li key={name}>
          <span className="service-health-version-name">{name}</span>
          {version}
        </li>
      ))}
    </ul>
  );
}

function ServiceHealth({ sessionContext, apiUrl }: ServiceHealthProps) {
  const { data, error, refresh, refreshing } = useDashboardApi<ServiceHealthData>(sessionContext, apiUrl, {
    maxAgeMs: REFRESH_MS,
    refreshMs: REFRESH_MS,
  });
  const checks = data?.health_checks ?? [];
  const failing = checks.filter((check) => !check.healthy).length;
  const level = healthLevel(data?.health_score ?? 0, failing);

  return (
    <section
      id="service-health"
      aria-label={gettext("Service Health")}
      aria-busy={!data && !error}
      // without data, the card is its own ghost: shimmering while it loads, still if it failed.
      className={`col-xl-6 mb-xl-10 ${!data && !error ? "service-health-loading" : ""}`}
    >
      <div className="card card-flush h-xl-100">
        <div className="card-header flex-nowrap pt-5">
          <div className="card-title align-items-start flex-column min-w-0">
            <h3 className="card-label fw-bold text-gray-800 m-0">{gettext("Service Health")}</h3>
            {data && (
              <span className="text-muted mt-1 fw-semibold fs-7">
                {interpolate(gettext("Smarter v%(smarter_version)s on %(linux_distribution)s"), {
                  smarter_version: data.smarter_version,
                  linux_distribution: data.linux_distribution,
                })}
              </span>
            )}
            {!data && <GhostHeader />}
          </div>
          {(data || error) && (
            <div className="card-toolbar align-self-start flex-shrink-0 ms-2">
              <button
                type="button"
                className="btn btn-sm btn-icon btn-light btn-active-light-primary"
                title={gettext("Run the health checks again now")}
                aria-label={gettext("Refresh service health")}
                disabled={refreshing}
                // the api runs the checks again, rather than answering from its cache.
                onClick={() => refresh({ refresh: true })}
              >
                <i className={`ki-outline ki-arrows-circle fs-3 ${refreshing ? "service-health-refreshing" : ""}`}></i>
              </button>
            </div>
          )}
        </div>
        <div className="card-body pt-2 pb-5 service-health-body">
          {data && <RuntimeVersions data={data} />}
          {!data && <GhostBody />}
          {error && (
            <p className="visually-hidden" role="status">
              {gettext("Service health couldn't be loaded. It will try again shortly.")}
            </p>
          )}
          {data && (
            <>
              <div className="d-flex align-items-center gap-4 mb-4">
                <HealthRing value={data.health_score} level={level} />
                <div className="flex-grow-1 min-w-0">
                  <div className="d-flex flex-wrap align-items-center justify-content-between gap-2 mb-2">
                    <div
                      className="service-health-label"
                      title={gettext(
                        "Live checks of the services that the platform needs, run each time this page loads.",
                      )}
                    >
                      {gettext("Backend services")}
                      <i className="ki-outline ki-information-5 fs-7 ms-1"></i>
                    </div>
                    <StatusBadge level={level} failing={failing} total={checks.length} />
                  </div>
                  <ul className="service-health-checks" aria-label={gettext("Backend services")}>
                    {checks.map((check) => (
                      <HealthCheckItem key={check.name} {...check} />
                    ))}
                  </ul>
                </div>
              </div>
              <div className="service-health-footer">
                <CIStatus repositoryUrl={data.repository_url} />
              </div>
            </>
          )}
        </div>
      </div>
    </section>
  );
}

export default ServiceHealth;

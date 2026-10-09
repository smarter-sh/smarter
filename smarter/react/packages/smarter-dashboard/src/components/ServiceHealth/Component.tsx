/**
 * ServiceHealth dashboard widget.
 *
 * This component fetches backend service metadata from an API endpoint and
 * renders platform health details, the results of the live checks of the
 * backing services, GitHub status, and runtime version information in a
 * dashboard card.
 *
 * :param apiUrl: Endpoint used to request service health and platform version
 *     data.
 * :type apiUrl: str
 *
 * :returns: A JSX element that renders loading, error, or service health
 *     dashboard content.
 * :rtype: JSX.Element
 *
 * :example:
 *
 *     <ServiceHealth apiUrl="https://api.smarter.sh/health" />
 */
import { useEffect, useState } from "react";
import { Loading } from "@smarter/common";

import { loggerPrefix } from "@/const";
import HealthRing from "@/components/ServiceHealth/HealthRing";
import GitHubStatus from "@/components/ServiceHealth/GitHubStatus";
import "@/components/ServiceHealth/styles.css";

interface ServiceHealthProps {
  apiUrl: string;
}

interface ServiceHealthData {
  linux_distribution: string;
  smarter_version: string;
  django_version: string;
  python_version: string;
  pydantic_version: string;
  drf_version: string;
  health_checks: HealthCheck[];
  health_score: number;
}

interface HealthCheck {
  name: string;
  healthy: boolean;
}

function HealthCheckItem({ name, healthy }: HealthCheck) {
  return (
    <span className="d-flex align-items-center fs-7 fw-bold text-gray-500 mb-2">
      <i
        className={`smarter-health-checks ki-outline ${healthy ? "ki-check text-success" : "ki-cross text-danger"} fs-6 me-2`}
        aria-label={healthy ? "healthy" : "unhealthy"}
      ></i>
      {name}
    </span>
  );
}

interface CardHeaderProps {
  smarter_version: string;
  linux_distribution: string;
}

function CardHeader({ smarter_version, linux_distribution }: CardHeaderProps) {
  return (
    <div className="card-header pt-5">
      {/* begin::Title */}
      <div className="row">
        <div className="col-12 border-bottom border-gray-200 pb-2 mb-2">
          <h4 className="card-title card-label fw-bold text-gray-800">Smarter v{smarter_version}</h4>
        </div>
        <div className="col-12 fw-bold text-gray-500 fs-6 mt-1">{linux_distribution}</div>
      </div>
      {/* end::Title */}
    </div>
  );
}

interface PlatformVersionsProps {
  python_version: string;
  django_version: string;
  pydantic_version: string;
  drf_version: string;
}

function PlatformVersions({ python_version, django_version, pydantic_version, drf_version }: PlatformVersionsProps) {
  return (
    <div className="row">
      <span className="col-12 text-gray-500 text-center mt-3 mb-0 pb-0 fs-9">
        Python {python_version} / Django {django_version} / Pydantic {pydantic_version} / DRF {drf_version}
      </span>
    </div>
  );
}

interface ServiceHealthChecksProps {
  healthChecks: HealthCheck[];
  healthScore: number;
}

function ServiceHealthChecks({ healthChecks, healthScore }: ServiceHealthChecksProps) {
  // two columns of checks
  const half = Math.ceil(healthChecks.length / 2);

  return (
    <div className="d-flex align-items-center mb-5">
      <div className="row m-0">
        <div className="col-3 d-flex justify-content-end">
          <div className="w-80px flex-shrink-0 me-2">
            <div
              className="min-h-auto ms-n3 d-none d-md-table-cell"
              id="kt_slider_widget_smarter_health"
              style={{ height: "100px" }}
            >
              <HealthRing value={healthScore} />
            </div>
          </div>
        </div>
        <div className="col-9">
          <h4 className="fw-bold text-gray-800 mb-3">Backend Service Health</h4>
          <div className="d-flex d-grid gap-5">
            <div className="d-flex flex-column flex-shrink-0 me-4">
              {healthChecks.slice(0, half).map((check) => (
                <HealthCheckItem key={check.name} {...check} />
              ))}
            </div>
            <div className="d-flex flex-column flex-shrink-0">
              {healthChecks.slice(half).map((check) => (
                <HealthCheckItem key={check.name} {...check} />
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function ServiceHealth({ apiUrl }: ServiceHealthProps) {
  const [data, setData] = useState<ServiceHealthData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    async function load() {
      try {
        setLoading(true);
        setError(null);

        const res = await fetch(apiUrl, {
          method: "POST",
          credentials: "same-origin",
          signal: controller.signal,
          headers: { Accept: "application/json" },
        });

        if (!res.ok) {
          throw new Error("Request failed: " + res.status);
        }

        const json = (await res.json()) as ServiceHealthData;
        console.debug(loggerPrefix, "Service Health data fetched from ", apiUrl, json);
        setData(json);
      } catch (err) {
        console.error(loggerPrefix, "Error loading Service Health:", err);
        if (err instanceof DOMException && err.name === "AbortError") return;
        setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        setLoading(false);
      }
    }

    load();
    return () => controller.abort();
  }, [apiUrl]);

  const smarter_version = data?.smarter_version ?? "0.0.0";
  const django_version = data?.django_version ?? "0.0.0";
  const python_version = data?.python_version ?? "0.0.0";
  const pydantic_version = data?.pydantic_version ?? "0.0.0";
  const drf_version = data?.drf_version ?? "0.0.0";
  const linux_distribution = data?.linux_distribution ?? "Unknown Linux distribution";
  const health_checks = data?.health_checks ?? [];
  const health_score = data?.health_score ?? 0;

  if (loading) return <Loading />;
  if (error) return <div>Failed to load service health: {error}</div>;

  return (
    <>
      {/* begin::Col */}
      <div id="service-health" aria-label="Service Health" className="col-xl-6 mb-xl-10">
        <div className="card card-flush h-xl-100">
          <CardHeader smarter_version={smarter_version} linux_distribution={linux_distribution} />
          <div className="card-body py-6">
            <ServiceHealthChecks healthChecks={health_checks} healthScore={health_score} />
            <GitHubStatus />
            <PlatformVersions
              python_version={python_version}
              django_version={django_version}
              pydantic_version={pydantic_version}
              drf_version={drf_version}
            />
          </div>
        </div>
      </div>
      {/* end::Col */}
    </>
  );
}

export default ServiceHealth;

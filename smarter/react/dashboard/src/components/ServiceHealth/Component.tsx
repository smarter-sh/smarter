// ----------------------------------------------------------------------------
// ServiceHealth Component.
// ----------------------------------------------------------------------------
import { useEffect, useState } from "react";
import HealthRing from "./HealthRing";
import GitHubStatus from "./GitHubStatus";
import "./styles.css";

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
}

interface HealthCheckItemProps {
  label: string;
}

function HealthCheckItem({ label }: HealthCheckItemProps) {
  return (
    <span className="d-flex align-items-center fs-7 fw-bold text-gray-500 mb-2">
      <i className="smarter-health-checks ki-duotone ki-check fs-6 me-2">
        <span className="path1"></span>
        <span className="path2"></span>
      </i>
      {label}
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
          <h4 className="card-title card-label fw-bold text-gray-800">
            Smarter v{smarter_version}
          </h4>
        </div>
        <div className="col-12 fw-bold text-gray-500 fs-6 mt-1">
          {linux_distribution}
        </div>
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
        Python {python_version} / Django {django_version} / Pydantic{" "}
        {pydantic_version} / DRF {drf_version}
      </span>
    </div>
  );
}


function ServiceHealthChecks() {
  const serviceHealthScore = 100;

  return (
    <div className="d-flex align-items-center mb-5">
      <div className="row m-0">
        <div className="col-3 d-flex justify-content-end">
          <div className="w-80px flex-shrink-0 me-2">
            <div
              className="min-h-auto ms-n3"
              id="kt_slider_widget_smarter_health"
              style={{ height: "100px" }}
            >
              <HealthRing value={serviceHealthScore} />
            </div>
          </div>
        </div>
        <div className="col-9">
          <h4 className="fw-bold text-gray-800 mb-3">Backend Service Health</h4>
          <div className="d-flex d-grid gap-5">
            <div className="d-flex flex-column flex-shrink-0 me-4">
              <HealthCheckItem label="Compute" />
              <HealthCheckItem label="Network" />
            </div>
            <div className="d-flex flex-column flex-shrink-0">
              <HealthCheckItem label="Data Storage" />
              <HealthCheckItem label="Ingress" />
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
        setData(json);
      } catch (err) {
        console.error("Error loading Service Health:", err);
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
  const linux_distribution =
    data?.linux_distribution ?? "Unknown Linux distribution";

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Failed to load service health: {error}</div>;

  return (
    <>
      {/* begin::Col */}
      <div
        id="service-health"
        aria-label="ServiceHealth"
        className="col-xl-6 mb-xl-10"
      >
        <div className="card card-flush h-xl-100">
          <CardHeader smarter_version={smarter_version} linux_distribution={linux_distribution} />
          <div className="card-body py-6">
            <ServiceHealthChecks />
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

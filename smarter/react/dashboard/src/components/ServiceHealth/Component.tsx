// ----------------------------------------------------------------------------
// ServiceHealth Component.
// ----------------------------------------------------------------------------
import { useEffect, useState } from "react";
import "./styles.css";

interface ServiceHealthProps {
  apiUrl: string;
}

interface ServiceHealthData {
  smarter_version: string;
  django_version: string;
  python_version: string;
}

function ServiceHealth({ apiUrl }: ServiceHealthProps) {
  const [data, setData] = useState<ServiceHealthData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    async function load() {
      try {
        console.log("Loading Service Health from API:", apiUrl);
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
        console.log("Loaded Service Health data:", json);
        setData(json);
      } catch (err) {
        console.error("Error loading Service Health:", err);
        if (err instanceof DOMException && err.name === "AbortError") return;
        setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        console.log("Finished loading Service Health");
        setLoading(false);
      }
    }

    load();
    return () => controller.abort();
  }, [apiUrl]);

  const smarter_version = data?.smarter_version ?? "0.0.0";
  const django_version = data?.django_version ?? "0.0.0";
  const python_version = data?.python_version ?? "0.0.0";

  console.log("ServiceHealth component received apiUrl:", apiUrl);

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
        {/* begin::Slider Widget 1 */}
        <div
          id="kt_sliders_widget_1_slider"
          className="card card-flush carousel carousel-custom carousel-stretch slide h-xl-100"
          data-bs-ride="carousel"
          data-bs-interval="5000"
        >
          {/* begin::Header */}
          <div className="card-header pt-5">
            {/* begin::Title */}
            <h4 className="card-title d-flex align-items-start flex-column">
              <span className="card-label fw-bold text-gray-800">
                Smarter {smarter_version}
              </span>
              <span className="text-gray-500 mt-1 fs-9">
                Python {python_version} / Django {django_version}
              </span>
              <span className="text-gray-500 mt-1 fw-bold fs-7">
                Backend Service Health
              </span>
            </h4>
            {/* end::Title */}
          </div>
          {/* end::Header */}
          {/* begin::Body */}
          <div className="card-body py-6">
            {/* begin::Item */}
            <div className="carousel-item active show">
              {/* begin::Wrapper */}
              <div className="d-flex align-items-center mb-5">
                {/* begin::Chart */}
                <div className="w-80px flex-shrink-0 me-2">
                  <div
                    className="min-h-auto ms-n3"
                    id="kt_slider_widget_smarter_health"
                    style={{ height: "100px" }}
                  ></div>
                </div>
                {/* end::Chart */}
                {/* begin::Info */}
                <div className="m-0">
                  {/* begin::Subtitle */}
                  <h4 className="fw-bold text-gray-800 mb-3">Infrastructure</h4>
                  {/* end::Subtitle */}
                  {/* begin::Items */}
                  <div className="d-flex d-grid gap-5">
                    {/* begin::Item */}
                    <div className="d-flex flex-column flex-shrink-0 me-4">
                      {/* begin::Section */}
                      <span className="d-flex align-items-center fs-7 fw-bold text-gray-500 mb-2">
                        <i className="smarter-health-checks ki-duotone ki-check fs-6 me-2">
                          <span className="path1"></span>
                          <span className="path2"></span>
                        </i>
                        Compute
                      </span>
                      {/* end::Section */}
                      {/* begin::Section */}
                      <span className="d-flex align-items-center text-gray-500 fw-bold fs-7">
                        <i className="smarter-health-checks ki-duotone ki-check fs-6 me-2">
                          <span className="path1"></span>
                          <span className="path2"></span>
                        </i>
                        Network
                      </span>
                      {/* end::Section */}
                    </div>
                    {/* end::Item */}
                    {/* begin::Item */}
                    <div className="d-flex flex-column flex-shrink-0">
                      {/* begin::Section */}
                      <span className="d-flex align-items-center fs-7 fw-bold text-gray-500 mb-2">
                        <i className="smarter-health-checks ki-duotone ki-check fs-6 me-2">
                          <span className="path1"></span>
                          <span className="path2"></span>
                        </i>
                        Data Storage
                      </span>
                      {/* end::Section */}
                      {/* begin::Section */}
                      <span className="d-flex align-items-center text-gray-500 fw-bold fs-7">
                        <i className="smarter-health-checks ki-duotone ki-check fs-6 me-2">
                          <span className="path1"></span>
                          <span className="path2"></span>
                        </i>
                        Ingress
                      </span>
                      {/* end::Section */}
                    </div>
                    {/* end::Item */}
                  </div>
                  {/* end::Items */}
                </div>
                {/* end::Info */}
              </div>
              {/* end::Wrapper */}
            </div>
            {/* end::Item */}
          </div>
          {/* end::Body */}
        </div>
        {/* end::Slider Widget 1 */}
      </div>
      {/* end::Col */}
    </>
  );
}

export default ServiceHealth;

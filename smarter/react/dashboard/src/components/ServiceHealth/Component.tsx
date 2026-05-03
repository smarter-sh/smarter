// ----------------------------------------------------------------------------
// ServiceHealth Component.
// ----------------------------------------------------------------------------
import "./styles.css";


interface ServiceHealthProps {
  apiUrl: string;
}

function ServiceHealth({ apiUrl }: ServiceHealthProps) {
  const smarter_version = "1.0.0"; // Example value, replace with actual data
  const django_version = "4.2.0"; // Example value, replace with actual data
  const python_version = "3.10.0"; // Example value, replace with actual data

  console.log("ServiceHealth component received apiUrl:", apiUrl);

  return (
    <>
      <section className="service-health" aria-label="ServiceHealth">
                  {/* begin::Col */}
          <div className="col-xl-6 mb-xl-10">
            {/* begin::Slider Widget 1 */}
            <div id="kt_sliders_widget_1_slider" className="card card-flush carousel carousel-custom carousel-stretch slide h-xl-100" data-bs-ride="carousel" data-bs-interval="5000">
              {/* begin::Header */}
              <div className="card-header pt-5">
                {/* begin::Title */}
                <h4 className="card-title d-flex align-items-start flex-column">
                  <span className="card-label fw-bold text-gray-800">Smarter { smarter_version }</span>
                  <span className="text-gray-500 mt-1 fs-9">Python { python_version } / Django { django_version }</span>
                  <span className="text-gray-500 mt-1 fw-bold fs-7">Backend Service Health</span>
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
                        <div className="min-h-auto ms-n3" id="kt_slider_widget_smarter_health" style={{ height: "100px" }}></div>
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
                            </i>Compute</span>
                            {/* end::Section */}
                            {/* begin::Section */}
                            <span className="d-flex align-items-center text-gray-500 fw-bold fs-7">
                            <i className="smarter-health-checks ki-duotone ki-check fs-6 me-2">
                              <span className="path1"></span>
                              <span className="path2"></span>
                            </i>Network</span>
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
                            </i>Data Storage</span>
                            {/* end::Section */}
                            {/* begin::Section */}
                            <span className="d-flex align-items-center text-gray-500 fw-bold fs-7">
                            <i className="smarter-health-checks ki-duotone ki-check fs-6 me-2">
                              <span className="path1"></span>
                              <span className="path2"></span>
                            </i>Ingress</span>
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

      </section>
    </>
  );
}

export default ServiceHealth;

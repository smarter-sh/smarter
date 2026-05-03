// ----------------------------------------------------------------------------
// CertificateProgram Component.
// ----------------------------------------------------------------------------
import "./styles.css";

interface CertificateProgramProps {
  apiUrl: string;
}

function CertificateProgram({ apiUrl }: CertificateProgramProps) {
  console.log("Rendering SelfHost with apiUrl:", apiUrl);

  return (
    <>
      {/* begin::Col */}
      <section
        id="certificate-program"
        aria-label="Certificate Program"
        className="col-xl-6 mb-5 mb-xl-10"
      >
        {/* begin::Slider Widget 2 */}
        <div
          id="kt_sliders_widget_2_slider"
          className="card card-flush carousel carousel-custom carousel-stretch slide h-xl-100"
          data-bs-ride="carousel"
          data-bs-interval="5500"
        >
          {/* begin::Header */}
          <div className="card-header pt-5">
            {/* begin::Title */}
            <h4 className="card-title d-flex align-items-start flex-column">
              <span className="card-label fw-bold text-gray-800">
                Certification Programs
              </span>
              <span className="text-gray-500 mt-1 fw-bold fs-7">
                Online self-paced and in demand
              </span>
            </h4>
            {/* end::Title */}
            {/* begin::Toolbar */}
            <div className="card-toolbar">
              {/* begin::Carousel Indicators */}
              <ol className="p-0 m-0 carousel-indicators carousel-indicators-bullet carousel-indicators-active-success">
                <li
                  data-bs-target="#kt_sliders_widget_2_slider"
                  data-bs-slide-to="0"
                  className="active ms-1"
                ></li>
                <li
                  data-bs-target="#kt_sliders_widget_2_slider"
                  data-bs-slide-to="1"
                  className="ms-1"
                ></li>
                <li
                  data-bs-target="#kt_sliders_widget_2_slider"
                  data-bs-slide-to="2"
                  className="ms-1"
                ></li>
              </ol>
              {/* end::Carousel Indicators */}
            </div>
            {/* end::Toolbar */}
          </div>
          {/* end::Header */}
          {/* begin::Body */}
          <div className="card-body py-6">
            {/* begin::Carousel */}
            <div className="carousel-inner">
              {/* begin::Item Prompt engineer */}
              <div className="carousel-item active show">
                {/* begin::Wrapper */}
                <div className="d-flex align-items-center mb-9">
                  {/* begin::Symbol */}
                  <div className="symbol symbol-70px symbol-circle me-5">
                    <span className="symbol-label bg-light-success">
                      <i className="ki-duotone ki-abstract-24 fs-3x text-success">
                        <span className="path1"></span>
                        <span className="path2"></span>
                      </i>
                    </span>
                  </div>
                  {/* end::Symbol */}
                  {/* begin::Info */}
                  <div className="m-0">
                    {/* begin::Subtitle */}
                    <h4 className="fw-bold text-gray-800 mb-3">
                      Prompt Engineer
                    </h4>
                    {/* end::Subtitle */}
                    {/* begin::Items */}
                    <div className="d-flex d-grid gap-5">
                      {/* begin::Item */}
                      <div className="d-flex flex-column flex-shrink-0 me-4">
                        {/* begin::Section */}
                        <span className="d-flex align-items-center fs-7 fw-bold text-gray-500 mb-2">
                          <i className="ki-duotone ki-right-square fs-6 text-gray-600 me-2">
                            <span className="path1"></span>
                            <span className="path2"></span>
                          </i>
                          4 Modules
                        </span>
                        {/* end::Section */}
                        {/* begin::Section */}
                        <span className="d-flex align-items-center text-gray-500 fw-bold fs-7">
                          <i className="ki-duotone ki-right-square fs-6 text-gray-600 me-2">
                            <span className="path1"></span>
                            <span className="path2"></span>
                          </i>
                          2 Instructors
                        </span>
                        {/* end::Section */}
                      </div>
                      {/* end::Item */}
                      {/* begin::Item */}
                      <div className="d-flex flex-column flex-shrink-0">
                        {/* begin::Section */}
                        <span className="d-flex align-items-center fs-7 fw-bold text-gray-500 mb-2">
                          <i className="ki-duotone ki-right-square fs-6 text-gray-600 me-2">
                            <span className="path1"></span>
                            <span className="path2"></span>
                          </i>
                          Approx 15 hours
                        </span>
                        {/* end::Section */}
                        {/* begin::Section */}
                        <span className="d-flex align-items-center text-gray-500 fw-bold fs-7">
                          <i className="ki-duotone ki-right-square fs-6 text-gray-600 me-2">
                            <span className="path1"></span>
                            <span className="path2"></span>
                          </i>
                          Fall 25 enrollment
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
                {/* begin::Action */}
                <div className="m-0">
                  <a
                    href="https://smarter.sh/"
                    className="btn btn-sm btn-light me-2 mb-2"
                  >
                    Details
                  </a>
                  <a
                    href="https://smarter.sh/"
                    className="btn btn-sm btn-success mb-2"
                  >
                    Apply
                  </a>
                </div>
                {/* end::Action */}
              </div>
              {/* end::Item Prompt engineer */}
              {/* begin::Item Developer */}
              <div className="carousel-item">
                {/* begin::Wrapper */}
                <div className="d-flex align-items-center mb-9">
                  {/* begin::Symbol */}
                  <div className="symbol symbol-70px symbol-circle me-5">
                    <span className="symbol-label bg-light-success">
                      <i className="ki-duotone ki-abstract-24 fs-3x text-success">
                        <span className="path1"></span>
                        <span className="path2"></span>
                      </i>
                    </span>
                  </div>
                  {/* end::Symbol */}
                  {/* begin::Info */}
                  <div className="m-0">
                    {/* begin::Subtitle */}
                    <h4 className="fw-bold text-gray-800 mb-3">Developer</h4>
                    {/* end::Subtitle */}
                    {/* begin::Items */}
                    <div className="d-flex d-grid gap-5">
                      {/* begin::Item */}
                      <div className="d-flex flex-column flex-shrink-0 me-4">
                        {/* begin::Section */}
                        <span className="d-flex align-items-center fs-7 fw-bold text-gray-500 mb-2">
                          <i className="ki-duotone ki-right-square fs-6 text-gray-600 me-2">
                            <span className="path1"></span>
                            <span className="path2"></span>
                          </i>
                          5 Topics
                        </span>
                        {/* end::Section */}
                        {/* begin::Section */}
                        <span className="d-flex align-items-center text-gray-500 fw-bold fs-7">
                          <i className="ki-duotone ki-right-square fs-6 text-gray-600 me-2">
                            <span className="path1"></span>
                            <span className="path2"></span>
                          </i>
                          1 Speakers
                        </span>
                        {/* end::Section */}
                      </div>
                      {/* end::Item */}
                      {/* begin::Item */}
                      <div className="d-flex flex-column flex-shrink-0">
                        {/* begin::Section */}
                        <span className="d-flex align-items-center fs-7 fw-bold text-gray-500 mb-2">
                          <i className="ki-duotone ki-right-square fs-6 text-gray-600 me-2">
                            <span className="path1"></span>
                            <span className="path2"></span>
                          </i>
                          60 Min
                        </span>
                        {/* end::Section */}
                        {/* begin::Section */}
                        <span className="d-flex align-items-center text-gray-500 fw-bold fs-7">
                          <i className="ki-duotone ki-right-square fs-6 text-gray-600 me-2">
                            <span className="path1"></span>
                            <span className="path2"></span>
                          </i>
                          137 students
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
                {/* begin::Action */}
                <div className="m-0">
                  <a
                    href="https://smarter.sh"
                    className="btn btn-sm btn-light me-2 mb-2"
                  >
                    Details
                  </a>
                  <a
                    href="https://smarter.sh"
                    className="btn btn-sm btn-success mb-2"
                  >
                    Apply
                  </a>
                </div>
                {/* end::Action */}
              </div>
              {/* end::Item Developer */}
              {/* begin::Item Administrator */}
              <div className="carousel-item">
                {/* begin::Wrapper */}
                <div className="d-flex align-items-center mb-9">
                  {/* begin::Symbol */}
                  <div className="symbol symbol-70px symbol-circle me-5">
                    <span className="symbol-label bg-light-danger">
                      <i className="ki-duotone ki-abstract-25 fs-3x text-danger">
                        <span className="path1"></span>
                        <span className="path2"></span>
                      </i>
                    </span>
                  </div>
                  {/* end::Symbol */}
                  {/* begin::Info */}
                  <div className="m-0">
                    {/* begin::Subtitle */}
                    <h4 className="fw-bold text-gray-800 mb-3">
                      Administrator
                    </h4>
                    {/* end::Subtitle */}
                    {/* begin::Items */}
                    <div className="d-flex d-grid gap-5">
                      {/* begin::Item */}
                      <div className="d-flex flex-column flex-shrink-0 me-4">
                        {/* begin::Section */}
                        <span className="d-flex align-items-center fs-7 fw-bold text-gray-500 mb-2">
                          <i className="ki-duotone ki-right-square fs-6 text-gray-600 me-2">
                            <span className="path1"></span>
                            <span className="path2"></span>
                          </i>
                          8 Modules
                        </span>
                        {/* end::Section */}
                        {/* begin::Section */}
                        <span className="d-flex align-items-center text-gray-500 fw-bold fs-7">
                          <i className="ki-duotone ki-right-square fs-6 text-gray-600 me-2">
                            <span className="path1"></span>
                            <span className="path2"></span>
                          </i>
                          1 Instructor
                        </span>
                        {/* end::Section */}
                      </div>
                      {/* end::Item */}
                      {/* begin::Item */}
                      <div className="d-flex flex-column flex-shrink-0">
                        {/* begin::Section */}
                        <span className="d-flex align-items-center fs-7 fw-bold text-gray-500 mb-2">
                          <i className="ki-duotone ki-right-square fs-6 text-gray-600 me-2">
                            <span className="path1"></span>
                            <span className="path2"></span>
                          </i>
                          Approx 30 hours
                        </span>
                        {/* end::Section */}
                        {/* begin::Section */}
                        <span className="d-flex align-items-center text-gray-500 fw-bold fs-7">
                          <i className="ki-duotone ki-right-square fs-6 text-gray-600 me-2">
                            <span className="path1"></span>
                            <span className="path2"></span>
                          </i>
                          Fall 25 enrollment
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
                {/* begin::Action */}
                <div className="m-0">
                  <a
                    href="https://smarter.sh"
                    className="btn btn-sm btn-light me-2 mb-2"
                  >
                    Details
                  </a>
                  <a
                    href="https://smarter.sh"
                    className="btn btn-sm btn-success mb-2"
                  >
                    Apply
                  </a>
                </div>
                {/* end::Action */}
              </div>
              {/* end::Item Administrator */}
            </div>
            {/* end::Carousel */}
          </div>
          {/* end::Body */}
        </div>
        {/* end::Slider Widget 2 */}
      </section>
      {/* end::Col */}
    </>
  );
}

export default CertificateProgram;

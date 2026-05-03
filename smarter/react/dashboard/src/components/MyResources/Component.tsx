// ----------------------------------------------------------------------------
// MyResources Component.
// ----------------------------------------------------------------------------
import "./styles.css";

interface MyResourcesProps {
  apiUrl: string;
}

function MyResources({ apiUrl }: MyResourcesProps) {
  console.log("MyResources component received apiUrl:", apiUrl);

  const my_resources_pending_deployments = 3; // Example value, replace with actual data
  const my_resources_chatbots = 5; // Example value, replace with actual data
  const my_resources_plugins = 2; // Example value, replace with actual data
  const my_resources_connections = 4; // Example value, replace with actual data
  const my_resources_providers = 6; // Example value, replace with actual data

  return (
    <>
        {/* begin::Col */}
        <section id="my-resources" aria-label="My Resources"className="col-xl-4 mb-xl-10">
          {/* begin::Lists Widget 19 */}
          <div className="card card-flush h-xl-100">
            {/* begin::Heading */}
            <div
              className="card-header rounded bgi-no-repeat bgi-size-cover bgi-position-y-top bgi-position-x-center align-items-start h-250px"
              style={{
                backgroundImage:
                  "url('/static/assets/media/svg/shapes/top-green.png')",
              }}
              data-bs-theme="light"
            >
              <img
                src="/static/assets/media/svg/files/ai.svg"
                className="position-absolute top-0 end-0 mt-3 me-3 h-75px"
                alt=""
              />

              {/* begin::Title */}
              <h3 className="card-title align-items-start flex-column text-white pt-15">
                <span className="fw-bold fs-2x mb-3">My Resources</span>
                <div className="fs-4 text-white">
                  {my_resources_pending_deployments > 0 && (
                    <>
                      <span className="opacity-75">You have</span>
                      <span className="position-relative d-inline-block">
                        <a
                          href="/prompts/"
                          className="link-white opacity-75-hover fw-bold d-block mb-1"
                        >
                          {my_resources_pending_deployments} pending
                        </a>
                        {/* begin::Separator */}
                        <span className="position-absolute opacity-50 bottom-0 start-0 border-2 border-body border-bottom w-100"></span>
                        {/* end::Separator */}
                      </span>
                      <span className="opacity-75">
                        {my_resources_pending_deployments > 1
                          ? "deployments"
                          : "deployment"}
                      </span>
                    </>
                  )}
                </div>
              </h3>
              {/* end::Title */}
            </div>
            {/* end::Heading */}
            {/* begin::Body */}
            <div className="card-body mt-n20">
              {/* begin::Stats */}
              <div className="mt-n20 position-relative">
                {/* begin::Row */}
                <div className="row g-3 g-lg-6">
                  {/* begin::Col */}
                  <div className="col-6">
                    {/* begin::Items */}
                    <a href="/prompts/">
                      <div className="bg-gray-100 bg-opacity-70 rounded-2 px-6 py-5">
                        {/* begin::Symbol */}
                        <div className="symbol symbol-30px me-5 mb-8">
                          <span className="symbol-label">
                            <i className="ki-duotone ki-technology-2 fs-1 text-primary">
                              <span className="path1"></span>
                              <span className="path2"></span>
                            </i>
                          </span>
                        </div>
                        {/* end::Symbol */}
                        {/* begin::Workbench */}
                        <div className="m-0">
                          {/* begin::Number */}
                          <span className="text-gray-700 fw-bolder d-block fs-2qx lh-1 ls-n1 mb-1">
                            {my_resources_chatbots}
                          </span>
                          {/* end::Number */}
                          {/* begin::Desc */}
                          <span className="text-gray-500 fw-semibold fs-6">
                            Agents
                          </span>
                          {/* end::Desc */}
                        </div>
                        {/* end::Workbench */}
                      </div>
                    </a>
                    {/* end::Items */}
                  </div>
                  {/* end::Col */}
                  {/* begin::Col */}
                  <div className="col-6">
                    {/* begin::Items */}
                    <div className="bg-gray-100 bg-opacity-70 rounded-2 px-6 py-5">
                      {/* begin::Symbol */}
                      <div className="symbol symbol-30px me-5 mb-8">
                        <span className="symbol-label">
                          <i className="ki-duotone ki-cube-2 fs-1 text-primary">
                            <span className="path1"></span>
                            <span className="path2"></span>
                          </i>
                        </span>
                      </div>
                      {/* end::Symbol */}

                      {/* begin::Plugins */}
                      <a href="/plugins/">
                        <div className="m-0">
                          {/* begin::Number */}
                          <span className="text-gray-700 fw-bolder d-block fs-2qx lh-1 ls-n1 mb-1">
                            {my_resources_plugins}
                          </span>
                          {/* end::Number */}
                          {/* begin::Desc */}
                          <span className="text-gray-500 fw-semibold fs-6">
                            Plugins
                          </span>
                          {/* end::Desc */}
                        </div>
                      </a>
                      {/* end::Plugins */}
                    </div>
                    {/* end::Items */}
                  </div>
                  {/* end::Col */}
                  {/* begin::Col */}
                  <div className="col-6">
                    {/* begin::Items */}
                    <div className="bg-gray-100 bg-opacity-70 rounded-2 px-6 py-5">
                      {/* begin::Symbol */}
                      <div className="symbol symbol-30px me-5 mb-8">
                        <span className="symbol-label">
                          <i className="ki-duotone ki-key fs-1 text-primary">
                            <span className="path1"></span>
                            <span className="path2"></span>
                            <span className="path3"></span>
                          </i>
                        </span>
                      </div>
                      {/* end::Symbol */}
                      {/* begin::Connections */}
                      <a
                        className="menu-link"
                        href="/connections/"
                        target="_self"
                      >
                        <div className="m-0">
                          {/* begin::Number */}
                          <span className="text-gray-700 fw-bolder d-block fs-2qx lh-1 ls-n1 mb-1">
                            {my_resources_connections}
                          </span>
                          {/* end::Number */}
                          {/* begin::Desc */}
                          <span className="text-gray-500 fw-semibold fs-6">
                            Connections
                          </span>
                          {/* end::Desc */}
                        </div>
                      </a>
                      {/* end::Connections */}
                    </div>
                    {/* end::Items */}
                  </div>
                  {/* end::Col */}
                  {/* begin::Col */}
                  <div className="col-6">
                    {/* begin::Items */}
                    <div className="bg-gray-100 bg-opacity-70 rounded-2 px-6 py-5">
                      {/* begin::Symbol */}
                      <div className="symbol symbol-30px me-5 mb-8">
                        <span className="symbol-label">
                          <i className="ki-duotone ki-bank fs-1 text-primary">
                            <span className="path1"></span>
                            <span className="path2"></span>
                            <span className="path3"></span>
                          </i>
                        </span>
                      </div>
                      {/* end::Symbol */}
                      {/* begin::Secrets */}
                      <a
                        className="menu-link"
                        href="/providers/"
                        target="_self"
                      >
                        <div className="m-0">
                          {/* begin::Number */}
                          <span className="text-gray-700 fw-bolder d-block fs-2qx lh-1 ls-n1 mb-1">
                            {my_resources_providers}
                          </span>
                          {/* end::Number */}
                          {/* begin::Desc */}
                          <span className="text-gray-500 fw-semibold fs-6">
                            Providers
                          </span>
                          {/* end::Desc */}
                        </div>
                      </a>
                      {/* end::Secrets */}
                    </div>
                    {/* end::Items */}
                  </div>
                  {/* end::Col */}
                </div>
                {/* end::Row */}
              </div>
              {/* end::Stats */}
            </div>
            {/* end::Body */}
          </div>
          {/* end::Lists Widget 19 */}
        </section>
        {/* end::Col */}
    </>
  );
}

export default MyResources;

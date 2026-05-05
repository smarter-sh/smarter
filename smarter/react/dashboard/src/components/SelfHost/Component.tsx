// ----------------------------------------------------------------------------
// SelfHost Component.
// ----------------------------------------------------------------------------
import "./styles.css";

interface SelfHostProps {
}

function SelfHost({  }: SelfHostProps) {
  return (
    <>
        {/* begin::Engage widget 4 */}
        <div
          id="self-host" aria-label="SelfHost"
          className="card border-transparent h-100"
          data-bs-theme="light"
          style={{ backgroundColor: "#1C325E" }}
        >
          {/* begin::Body */}
          <div className="row w-100">
            <div className="card-body d-flex flex-column ps-xl-15 h-100">
              {/* begin::Title */}
              <div className="position-relative fs-2x z-index-2 fw-bold text-white mb-7">
                <span className="position-relative d-inline-block text-danger">
                  <a
                    href="https://docs.smarter.sh/en/latest/smarter-platform/installation.html"
                    target="_blank"
                    className="btn btn-primary fw-semibold me-2 opacity-75-hover"
                  >
                    Installation Guide
                  </a>
                  <span className="me-2"> Self-host Smarter</span>
                </span>
              </div>
              {/* end::Title */}
              {/* begin::Illustration */}
              <img
                src="/static/assets/media/illustrations/sigma-1/14-dark-white-bkg.png"
                className="position-absolute me-3 bottom-0 end-0 w-100"
                alt=""
              />
              <img
                src="/static/images/docker-logo.png"
                className="position-absolute top-50 end-0 me-20 w-100px"
                style={{ transform: "translateY(-100%)" }}
                alt=""
              />
              {/* end::Illustration */}

              <div
                className="text-white mt-auto mb-0 pt-5 align-self-end rounded"
                style={{
                  width: "50%",
                  background: "rgba(34, 34, 34, 0.25)",
                  zIndex: 10,
                  position: "relative",
                }}
              >
                <ul style={{ listStyle: "none", paddingLeft: 0 }}>
                  <li className="ps-4">
                    <span
                      style={{
                        color: "#888",
                        fontSize: "1.2em",
                        marginRight: "0.5em",
                      }}
                    >
                      &#8594;
                    </span>
                    <a
                      href="https://github.com/smarter-sh/smarter-deploy"
                      target="_blank"
                      className="text-gray-200"
                    >
                      Docker
                    </a>
                  </li>
                  <li className="ps-4">
                    <span
                      style={{
                        color: "#888",
                        fontSize: "1.2em",
                        marginRight: "0.5em",
                      }}
                    >
                      &#8594;
                    </span>
                    <a
                      href="https://artifacthub.io/packages/helm/project-smarter/smarter"
                      target="_blank"
                      className="text-gray-200"
                    >
                      Kubernetes
                    </a>
                  </li>
                  <li className="ps-4">
                    <span
                      style={{
                        color: "#888",
                        fontSize: "1.2em",
                        marginRight: "0.5em",
                      }}
                    >
                      &#8594;
                    </span>
                    <a
                      href="https://github.com/smarter-sh/smarter-infrastructure"
                      target="_blank"
                      className="text-gray-200"
                    >
                      Terraform
                    </a>
                  </li>
                </ul>
              </div>
            </div>
          </div>
          {/* end::Body */}
        </div>
        {/* end::Engage widget 4 */}
    </>
  );
}

export default SelfHost;

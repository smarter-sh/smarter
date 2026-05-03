// ----------------------------------------------------------------------------
// DownloadNpm Component.
// ----------------------------------------------------------------------------
import "./styles.css";

interface DownloadNpmProps {
  apiUrl: string;
}

function DownloadNpm({ apiUrl }: DownloadNpmProps) {
  console.log("Rendering DownloadNpm with apiUrl:", apiUrl);
  return (
    <>
      <section
        id="download-npm"
        aria-label="Download Npm"
        className="col-xl-4 mb-xl-10"
      >
        {/* begin::Download NPM widget 4 */}
        <div
          className="card border-transparent"
          data-bs-theme="light"
          style={{ backgroundColor: "#1C325E" }}
        >
          {/* begin::Body */}
          <div className="card-body d-flex ps-xl-15">
            {/* begin::Wrapper */}
            <div className="m-0">
              {/* begin::Title */}
              <div className="position-relative fs-2x z-index-2 fw-bold text-white mb-7">
                <span className="me-2">React Chat component on NPM</span>
                {/* end::Title */}
                {/* begin::Action */}
                <div className="m-3 mt-5 text-center">
                  <a
                    href="https://www.npmjs.com/package/@smarter.sh/ui-chat"
                    target="_blank"
                    className="btn btn-danger fw-semibold me-2"
                  >
                    Download
                  </a>
                </div>
                {/* end::Action */}
              </div>
              {/* end::Wrapper */}
              {/* begin::Illustration */}
              <img
                src="/static/images/npm-logo.png"
                className="position-absolute me-3 top-0 end-0 h-75px pt-3"
                alt=""
              />
              {/* end::Illustration */}
            </div>
            {/* end::Body */}
          </div>
          {/* end::Download NPM widget 4 */}
        </div>
      </section>
    </>
  );
}

export default DownloadNpm;

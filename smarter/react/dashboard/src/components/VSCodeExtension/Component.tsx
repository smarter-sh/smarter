// ----------------------------------------------------------------------------
// VSCodeExtension Component.
// ----------------------------------------------------------------------------
import "./styles.css";

interface VSCodeExtensionProps {
}

function VSCodeExtension({  }: VSCodeExtensionProps) {
  return (
    <>
      {/* begin::Download VS Code Extension widget 4 */}
      <div
        id="vscode-extension"
        aria-label="VSCodeExtension"
        className="card border-transparent"
        data-bs-theme="light"
        style={{ backgroundColor: "#23272e" }}
      >
        {/* begin::Body */}
        <div className="card-body d-flex ps-xl-15">
          {/* begin::Wrapper */}
          <div className="m-0">
            {/* begin::Title */}
            <div className="position-relative fs-2x z-index-2 fw-bold text-white mb-0">
              {/* begin::Title */}
              <span className="me-2">
                Get the
                <span className="position-relative d-inline-block text-danger mb-2">
                  <a
                    href="https://marketplace.visualstudio.com/items?itemName=Querium.smarter-manifest"
                    className="text-danger opacity-75-hover"
                  >
                    VS Code Extension
                  </a>
                  {/* begin::Separator */}
                  <span className="position-absolute opacity-50 bottom-0 start-0 border-4 border-danger border-bottom w-100 p-3"></span>
                  {/* end::Separator */}
                </span>
              </span>
              {/* end::Title */}
              <p
                className="text-gray-200 fs-6 fw-normal mt-3 mb-10"
                style={{ maxWidth: "80%" }}
              >
                The Smarter Manifest VS Code Extension provides intelligent
                syntax checking, context-sensitive microhelp, and real-time code
                suggestions.
              </p>
              {/* end::Title */}
              {/* begin::Action */}
              <div className="m-3 mt-5 text-center">
                <a
                  href="https://marketplace.visualstudio.com/items?itemName=Querium.smarter-manifest"
                  target="_blank"
                  className="btn btn-primary fw-semibold me-2"
                >
                  Download
                </a>
                <a
                  href="https://docs.smarter.sh/en/latest/smarter-framework/vs-code-extension.html"
                  target="_blank"
                  className="btn btn-secondary fw-semibold me-2"
                >
                  Documentation
                </a>
              </div>
              {/* end::Action */}
            </div>
            {/* end::Wrapper */}
            {/* begin::Illustration */}
            <img
              src="/static/images/vs-code-logo.png"
              className="position-absolute me-5 mt-3 top-0 end-0 h-100px pt-3"
              alt=""
            />
            {/* end::Illustration */}
          </div>
          {/* end::Body */}
        </div>
        {/* end::Download VS Code Extension widget 4 */}
      </div>
    </>
  );
}

export default VSCodeExtension;

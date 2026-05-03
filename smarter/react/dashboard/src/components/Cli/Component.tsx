// ----------------------------------------------------------------------------
// CLI Component.
// ----------------------------------------------------------------------------
import "./styles.css";

interface CliProps {
  apiUrl: string;
}

function Cli({ apiUrl }: CliProps) {
  console.log("Rendering Cli with apiUrl:", apiUrl);
  return (
    <>
      <section id="cli" aria-label="CLI" className="col-xl-4 mb-5 mb-xl-10">
        {/* begin::Engage widget 4 */}
        <div className="card border-transparent" data-bs-theme="light">
          {/* begin::Body */}
          <div className="card-body d-flex flex-column ps-xl-15 h-100">
            {/* begin::Wrapper */}
            <div className="m-0">
              {/* begin::Title */}
              <h6 className="text-muted opacity-75-hover me-2 fs-3 fw-bold">
                Smarter Command-line interface
              </h6>
              {/* end::Title */}
              <p className="mb-10">
                Powerful tools for managing your AI resources.
              </p>
              {/* begin::Action */}
              <div className="mb-3">
                <a
                  href="https://smarter.sh/cli/"
                  target="_blank"
                  className="btn btn-sm btn-dark fw-semibold me-2"
                >
                  Download
                </a>
                <a
                  href="https://docs.smarter.sh/en/latest/smarter-framework/smarter-cli.html"
                  target="_blank"
                  className="btn btn-sm btn-secondary text-dark fw-semibold"
                >
                  Documentation
                </a>
              </div>
              {/* end::Action */}
            </div>
            {/* end::Wrapper */}
          </div>
          {/* end::Body */}
        </div>
        {/* end::Engage widget 4 */}
      </section>
    </>
  );
}

export default Cli;

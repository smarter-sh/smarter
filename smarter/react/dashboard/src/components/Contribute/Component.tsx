// ----------------------------------------------------------------------------
// Contribute Component.
// ----------------------------------------------------------------------------
import "./styles.css";

interface ContributeProps {
}

function Contribute({  }: ContributeProps) {
  return (
    <>
      {/* begin::Engage widget 4 */}
      <section
        id="contribute"
        aria-label="Contribute"
        className="card border-transparent h-100"
        data-bs-theme="light"
      >
        {/* begin::Body */}
        <div className="row w-100">
          <div className="card-body d-flex flex-column ps-xl-15 h-100">
            {/* begin::Title */}
            <h6 className="text-muted  opacity-75-hover w-100 my-4 fs-3 fw-bold">
              Contribute to Smarter
            </h6>
            {/* end::Title */}

            <p
              className="text-gray-700 fs-6 fw-normal mt-3 mb-10 w-50"
              style={{ maxWidth: "50%" }}
            >
              Start small, learn by doing, and help improve Smarter while you
              discover how real Python projects work.
            </p>

            <div className="bottom-0 start-0 mb-5 ms-5">
              <ul>
                <li className="mb-2">
                  <a
                    href="https://github.com/smarter-sh/smarter/"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-white/80 hover:text-white transition-colors"
                  >
                    <img
                      src="https://img.shields.io/github/v/release/smarter-sh/smarter?style=flat&color=ea580c"
                      alt="Latest Release"
                    />
                  </a>
                </li>
                <li className="mb-2">
                  <a
                    href="https://github.com/smarter-sh/smarter/stargazers"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-white/80 hover:text-white transition-colors"
                  >
                    <img
                      src="https://img.shields.io/github/stars/smarter-sh/smarter?style=flat&color=ea580c"
                      alt="GitHub Stars"
                    />
                  </a>
                </li>
                <li className="mb-2">
                  <a
                    href="https://github.com/smarter-sh/smarter/network/members"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-white/80 hover:text-white transition-colors"
                  >
                    <img
                      src="https://img.shields.io/github/forks/smarter-sh/smarter?style=flat&color=ea580c"
                      alt="GitHub Forks"
                    />
                  </a>
                </li>
              </ul>
            </div>

            {/* begin::Illustration */}
            <img
              src="/static/assets/media/illustrations/dozzy-1/13-dark.png"
              className="position-absolute me-3 bottom-0 end-0 h-250px"
              alt=""
            />
            {/* end::Illustration */}
          </div>
        </div>
        {/* end::Body */}
      </section>
      {/* end::Engage widget 4 */}
    </>
  );
}

export default Contribute;

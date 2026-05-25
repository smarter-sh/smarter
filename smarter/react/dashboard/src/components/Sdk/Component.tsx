/**
 * Sdk dashboard widget.
 *
 * This component renders developer SDK resource links and related branding
 * assets, including references to the React NPM package and Python PyPI
 * library.
 *
 * :param props: Component props.
 * :type props: SdkProps
 *
 * :returns: A JSX fragment containing SDK resource links and supporting banner
 *     content.
 * :rtype: JSX.Element
 *
 * :example:
 *
 *     <Sdk />
 */
import "./styles.css";

interface SdkProps {
}

function Sdk({  }: SdkProps) {
  return (
    <>
      <div id="sdk" aria-label="SDK" className="col-xl-4 mb-5 mb-xl-10">
        {/* begin::SDKs */}
        <div className="card border-transparent" data-bs-theme="light">
          {/* begin::Body */}
          <div className="card-body d-flex flex-column ps-xl-15 h-100">
            {/* begin::Title */}
            <h6 className="text-muted  opacity-75-hover w-100 my-4 fs-3 fw-bold">
              Smarter Developer SDKs
            </h6>
            {/* end::Title */}
            {/* begin::Action */}
            <div className="mb-3">
              <ul style={{ listStyle: "none", paddingLeft: 0 }}>
                <li>
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
                    href="https://www.npmjs.com/package/@smarter.sh/ui-chat"
                    target="_blank"
                    className="text-dark"
                  >
                    <span>
                      <img
                        src="/static/assets/media/framework-logos/react.png"
                        className="h-10px"
                        alt="ReactJS Logo"
                      />
                    </span>
                    React NPM Package
                  </a>
                </li>
                <li>
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
                    href="https://pypi.org/project/smarter-api/"
                    target="_blank"
                    className="text-dark"
                  >
                    <span>
                      <img
                        src="/static/images/python-logo.png"
                        className="h-10px"
                        alt="Python Logo"
                      />
                    </span>
                    Python PyPi Library
                  </a>
                </li>
              </ul>
            </div>
            {/* end::Action */}
            {/* begin::Illustrations */}
            <img
              src="/static/images/npm-logo.png"
              className="position-absolute me-3 top-0 end-0 h-75px pt-3 d-none d-xl-table-cell"
              alt="NPM Logo"
            />
            <img
              src="/static/images/pypi-logo-small.svg"
              className="position-absolute me-5 bottom-0 end-0 h-75px pt-3 mb-3 d-none d-xl-table-cell"
              alt="PyPI Logo"
            />
            {/* end::Illustrations */}
          </div>
          {/* end::Body */}
        </div>
        {/* end::SDKs */}
      </div>

      <div className="col-xl-4 mb-5 mb-xl-10 h-100">
        {/* begin::Row Developer/enthusiast banner */}
        <div className="mt-15 text-center">
          <h2 className="text-gray-600">
            Resources for Developers, Solution Architects, and Enterprise Users
          </h2>
        </div>
      </div>
    </>
  );
}

export default Sdk;

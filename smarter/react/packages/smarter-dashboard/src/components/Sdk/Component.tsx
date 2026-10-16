/**
 * Sdk dashboard widget.
 *
 * This component renders a promotional card for the Smarter developer SDKs:
 * the smarter-chat NPM package (@smarter.sh/ui-chat), the Node.js SDK
 * (@smarter.sh/api), the Python PyPI library (smarter-api) and the Go module
 * (github.com/smarter-sh/smarter-golang). Each SDK shows its logo, links to its
 * package registry, and shows its install command, followed by links to the
 * APIs and SDKs documentation and to this platform's OpenAPI document.
 *
 * :returns: A JSX fragment containing the SDK call-to-action widget.
 * :rtype: JSX.Element
 *
 * :example:
 *
 *     <Sdk />
 */
import "@/components/Sdk/styles.css";
import { gettext, interpolateNodes } from "@smarter/common";

/** This platform's OpenAPI document, which every platform serves in its web console. */
const OPENAPI_URL = "/docs/openapi/";

const SDKS = [
  {
    name: "smarter-chat NPM Package",
    href: "https://www.npmjs.com/package/@smarter.sh/ui-chat",
    logo: "/static/assets/media/svg/brand-logos/react.svg",
    install: "npm install @smarter.sh/ui-chat",
  },
  {
    name: "Node.js SDK",
    href: "https://www.npmjs.com/package/@smarter.sh/api",
    logo: "/static/images/sdks/nodedotjs.svg",
    install: "npm install @smarter.sh/api",
  },
  {
    name: "Python PyPi Library",
    href: "https://pypi.org/project/smarter-api/",
    logo: "/static/assets/media/svg/brand-logos/python-5.svg",
    install: "pip install smarter-api",
  },
  {
    name: "Go SDK",
    href: "https://pkg.go.dev/github.com/smarter-sh/smarter-golang",
    logo: "/static/images/sdks/go.svg",
    install: "go get github.com/smarter-sh/smarter-golang",
  },
];

function Sdk() {
  return (
    <>
      <section id="sdk" aria-label={gettext("SDK")} className="col-xl-4 mb-5 mb-xl-10">
        {/* begin::SDKs widget */}
        <div className="card border-transparent h-100 sdk-card" data-bs-theme="light">
          {/* begin::Body */}
          <div className="card-body d-flex flex-column ps-xl-15 h-100 position-relative">
            {/* begin::Illustration */}
            <img
              src="/static/assets/media/illustrations/dozzy-1/4.png"
              className="position-absolute top-0 end-0 h-100px me-1 mt-1"
              alt=""
            />
            {/* end::Illustration */}
            {/* begin::Title */}
            <div className="position-relative fs-2x fw-bold text-gray-900 mb-2 z-index-2">
              {/* Translators: a headline. %(span)s is its highlighted last words, translated separately. */}
              {interpolateNodes(gettext("Build with the %(span)s"), {
                span: (
                  <span className="position-relative d-inline-block">
                    {/* Translators: the highlighted words of a headline. %(span)s is their decorative underline, and stays at the end. */}
                    {interpolateNodes(gettext("SDKs%(span)s"), {
                      span: (
                        <span className="position-absolute opacity-50 bottom-0 start-0 border-4 border-danger border-bottom w-100"></span>
                      ),
                    })}
                  </span>
                ),
              })}
            </div>
            <p className="text-gray-700 fs-6 mb-7 z-index-2 sdk-lede">
              {gettext("Typed access to your Smarter resources, in the language you already use.")}
            </p>
            {/* end::Title */}
            {/* begin::SDKs */}
            <ul className="sdk-list z-index-2">
              {SDKS.map((sdk) => (
                <li key={sdk.name} className="sdk-item">
                  <span className="sdk-logo">
                    <img src={sdk.logo} alt="" />
                  </span>
                  <span className="sdk-text">
                    <a href={sdk.href} target="_blank" className="sdk-name">
                      {sdk.name}
                    </a>
                    <span className="sdk-install">{sdk.install}</span>
                  </span>
                </li>
              ))}
            </ul>
            {/* end::SDKs */}
            {/* begin::Action */}
            <div className="d-flex flex-wrap gap-2 mt-auto pt-7 z-index-2">
              <a
                href="https://docs.smarter.sh/en/latest/smarter-framework/apis-and-sdks.html"
                target="_blank"
                className="btn btn-sm btn-danger fw-semibold"
              >
                {gettext("Documentation")}
              </a>
              <a href={OPENAPI_URL} className="btn btn-sm btn-light-danger fw-semibold">
                {gettext("API reference")}
              </a>
              <a
                href="https://github.com/smarter-sh"
                target="_blank"
                className="btn btn-sm btn-dark fw-semibold"
                aria-label={gettext("SDK source code")}
              >
                {gettext("GitHub")}
              </a>
            </div>
            {/* end::Action */}
          </div>
          {/* end::Body */}
        </div>
        {/* end::SDKs widget */}
      </section>
    </>
  );
}

export default Sdk;

/**
 * Extensions dashboard widget.
 *
 * This component renders a card about Smarter Extensions: Python packages
 * that add tools to a platform's LLMs, installed by superusers from the
 * signed Smarter Extension registry without a redeploy, and listed in an
 * LLMClient's ``spec.extensions``. It shows the three official extensions
 * with their trust badge and a link to its GitHub repository, a manifest that uses one, and links to the
 * documentation, the registry, and the guide to building an extension.
 *
 * :returns: A JSX fragment containing the Extensions widget.
 * :rtype: JSX.Element
 *
 * :example:
 *
 *     <Extensions />
 */
import "./styles.css";
import { gettext, interpolateNodes } from "@smarter/common";

const DOCS = "https://docs.smarter.sh/en/latest";

const EXTENSIONS = [
  {
    slug: "weather",
    name: "Weather",
    description: gettext("Current weather and a 24-hour forecast for any location."),
    icon: "ki-cloud",
  },
  {
    slug: "calculator",
    name: "Calculator",
    description: gettext("Evaluates math expressions exactly, so that LLMs don't guess."),
    icon: "ki-calculator",
  },
  {
    slug: "date-calculator",
    name: "Date Calculator",
    description: gettext("Date arithmetic: differences, adding and subtracting days."),
    icon: "ki-calendar",
  },
];

const STEPS = [
  gettext("Browse the registry"),
  gettext("Install, signature-checked"),
  gettext("Enable, then list it in a manifest"),
];

function Extensions() {
  return (
    <>
      <section id="extensions" aria-label={gettext("Extensions")} className="card border-transparent extensions-card">
        <div className="card-body ps-xl-15">
          <div className="row g-7 align-items-center">
            {/* begin::Pitch */}
            <div className="col-md-6">
              <span className="extensions-eyebrow">{gettext("New in 0.27")}</span>
              <div className="fs-2x fw-bold text-gray-900 mt-3 mb-2">
                {/* Translators: a headline. %(span)s is its highlighted last words, translated separately. */}
                {interpolateNodes(gettext("Add tools with %(span)s"), {
                  span: (
                    <span className="position-relative d-inline-block">
                      {/* Translators: the highlighted words of a headline. %(span)s is their decorative underline, and stays at the end. */}
                      {interpolateNodes(gettext("Extensions%(span)s"), {
                        span: (
                          <span className="position-absolute bottom-0 start-0 border-4 border-bottom w-100 extensions-underline"></span>
                        ),
                      })}
                    </span>
                  ),
                })}
              </div>
              <p className="text-gray-700 fs-6 mb-4">
                {gettext(
                  "Python packages that give your LLMs new tools, installed from the signed Smarter Extension registry without a redeploy.",
                )}
              </p>
              <ol className="extensions-steps">
                {STEPS.map((step, index) => (
                  <li key={step}>
                    <span className="extensions-step-number">{index + 1}</span>
                    {step}
                  </li>
                ))}
              </ol>
              <div className="d-flex flex-wrap gap-2 mt-5">
                <a
                  href={`${DOCS}/smarter-platform/extensions.html`}
                  target="_blank"
                  className="btn btn-sm fw-semibold extensions-btn"
                >
                  {gettext("How extensions work")}
                </a>
                <a
                  href="https://github.com/smarter-sh/extensions-registry"
                  target="_blank"
                  className="btn btn-sm btn-light fw-semibold"
                >
                  {gettext("Browse the registry")}
                </a>
                <a
                  href={`${DOCS}/smarter-framework/smarter-extensions.html`}
                  target="_blank"
                  className="align-self-center fw-semibold extensions-link"
                >
                  {gettext("Build one →")}
                </a>
              </div>
            </div>
            {/* end::Pitch */}
            {/* begin::Registry */}
            <div className="col-md-6">
              <ul className="extensions-list" aria-label={gettext("Official extensions")}>
                {EXTENSIONS.map((extension) => (
                  <li key={extension.slug}>
                    <a
                      href={`https://github.com/smarter-sh/smarter-extension-${extension.slug}`}
                      target="_blank"
                      rel="noreferrer"
                      className="extensions-item"
                    >
                      <span className="extensions-icon">
                        <i className={`ki-outline ${extension.icon} fs-2`}></i>
                      </span>
                      <span className="extensions-text">
                        <span className="extensions-name">
                          {extension.name}
                          <span className="extensions-badge">{gettext("Official")}</span>
                        </span>
                        <span className="extensions-description">{extension.description}</span>
                      </span>
                    </a>
                  </li>
                ))}
              </ul>
              <pre className="extensions-manifest" aria-label={gettext("An LLMClient manifest that uses an extension")}>
                <span className="extensions-key">kind</span>: <span className="extensions-str">LLMClient</span>
                {"\n"}
                <span className="extensions-key">spec</span>:{"\n"}
                {"  "}
                <span className="extensions-key">extensions</span>:{"\n"}
                {"    "}- <span className="extensions-str">weather</span>
              </pre>
            </div>
            {/* end::Registry */}
          </div>
        </div>
      </section>
    </>
  );
}

export default Extensions;

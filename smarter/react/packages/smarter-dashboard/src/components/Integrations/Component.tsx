/**
 * Integrations dashboard widget.
 *
 * This component renders a promotional card for the Smarter Chat
 * integrations, which add a deployed LLMClient's chat to a third-party
 * platform with @smarter.sh/ui-chat's embed script: the WordPress plugin, the
 * Drupal module, the Shopify app, the Google Tag Manager template, and the
 * plugins for the Docusaurus, MkDocs, Sphinx and VitePress documentation site
 * generators. Each integration is a logo tile that links to its
 * documentation, followed by links to the embedding guide and the source code.
 *
 * :returns: A JSX fragment containing the integrations call-to-action widget.
 * :rtype: JSX.Element
 *
 * :example:
 *
 *     <Integrations />
 */
import "@/components/Integrations/styles.css";

const DOCS = "https://docs.smarter.sh/en/latest/smarter-framework";

const INTEGRATIONS = [
  {
    name: "WordPress",
    logo: "/static/images/integrations/wordpress.svg",
    docs: `${DOCS}/smarter-wordpress.html`,
  },
  {
    name: "Drupal",
    logo: "/static/images/integrations/drupal.svg",
    docs: `${DOCS}/smarter-drupal.html`,
  },
  {
    name: "Shopify",
    logo: "/static/images/integrations/shopify.svg",
    docs: `${DOCS}/smarter-shopify.html`,
  },
  {
    name: "Google Tag Manager",
    logo: "/static/assets/media/svg/brand-logos/google-tag-manager.svg",
    docs: `${DOCS}/smarter-gtm.html`,
  },
  {
    name: "Docusaurus",
    logo: "/static/images/integrations/docusaurus.svg",
    docs: `${DOCS}/smarter-docs-sites.html`,
  },
  {
    name: "MkDocs",
    logo: "/static/images/integrations/materialformkdocs.svg",
    docs: `${DOCS}/smarter-docs-sites.html`,
  },
  {
    name: "Sphinx",
    logo: "/static/images/integrations/sphinx.svg",
    docs: `${DOCS}/smarter-docs-sites.html`,
  },
  {
    name: "VitePress",
    logo: "/static/images/integrations/vitepress.svg",
    docs: `${DOCS}/smarter-docs-sites.html`,
  },
];

function Integrations() {
  return (
    <>
      <section id="integrations" aria-label="Integrations" className="col-xl-4 mb-5 mb-xl-10">
        {/* begin::Integrations widget */}
        <div className="card border-transparent h-100 integrations-card" data-bs-theme="light">
          {/* begin::Body */}
          <div className="card-body d-flex flex-column ps-xl-15 h-100 position-relative">
            {/* begin::Illustration */}
            <img
              src="/static/assets/media/illustrations/sketchy-1/17-dark.png"
              className="position-absolute top-0 end-0 h-125px me-3 mt-3 integrations-illustration"
              alt=""
            />
            {/* end::Illustration */}
            {/* begin::Title */}
            <div className="position-relative fs-2x fw-bold text-white mb-2 z-index-2">
              Put your chatbot{" "}
              <span className="position-relative d-inline-block">
                everywhere
                <span className="position-absolute opacity-50 bottom-0 start-0 border-4 border-warning border-bottom w-100"></span>
              </span>
            </div>
            <p className="text-white opacity-75 fs-6 mb-7 z-index-2 integrations-lede">
              Add Smarter Chat to the sites your users already visit, with one setting.
            </p>
            {/* end::Title */}
            {/* begin::Logos */}
            <ul className="integrations-grid z-index-2">
              {INTEGRATIONS.map((integration) => (
                <li key={integration.name}>
                  <a
                    href={integration.docs}
                    target="_blank"
                    className="integrations-tile hover-elevate-up"
                    title={integration.name}
                  >
                    <span className="integrations-logo">
                      <img src={integration.logo} alt="" />
                    </span>
                    <span className="integrations-name">{integration.name}</span>
                  </a>
                </li>
              ))}
            </ul>
            {/* end::Logos */}
            {/* begin::Action */}
            <div className="mt-auto pt-7 z-index-2">
              <a
                href={`${DOCS}/smarter-chat/embedding.html`}
                target="_blank"
                className="btn btn-sm btn-warning fw-semibold me-2"
              >
                Embedding guide
              </a>
              <a
                href="https://github.com/smarter-sh"
                target="_blank"
                className="btn btn-sm btn-light fw-semibold"
                aria-label="Integrations source code"
              >
                GitHub
              </a>
            </div>
            {/* end::Action */}
          </div>
          {/* end::Body */}
        </div>
        {/* end::Integrations widget */}
      </section>
    </>
  );
}

export default Integrations;

/**
 * WhatsNew dashboard widget.
 *
 * This component renders a card that highlights notable features added in
 * recent Smarter releases, with each entry linking to its documentation page
 * on docs.smarter.sh.
 *
 * :returns: A JSX fragment containing the new features widget.
 * :rtype: JSX.Element
 *
 * :example:
 *
 *     <WhatsNew />
 */
import "@/components/WhatsNew/styles.css";

interface Feature {
  name: string;
  version: string;
  description: string;
  docsPath: string;
}

const DOCS_BASE_URL = "https://docs.smarter.sh";

const FEATURES: Feature[] = [
  {
    name: "Extensions",
    version: "0.27",
    description: "Install signed, third-party LLM tools from the Smarter Extension registry",
    docsPath: "smarter-platform/extensions.html",
  },
  {
    name: "Smarter MCP Server",
    version: "0.24",
    description: "Answers about The Smarter Project, from its own code and docs, for any MCP client",
    docsPath: "smarter-platform/smarter-project-mcp-server.html",
  },
  {
    name: "OpenAPI",
    version: "0.22",
    description: "An OpenAPI document and JSON Schemas for the Smarter api, served by every platform",
    docsPath: "smarter-framework/smarter-openapi.html",
  },
  {
    name: "Themable Chat",
    version: "0.21",
    description: "Brand your LLMClient's chat with your own logo, colors, fonts and avatar",
    docsPath: "smarter-resources/llmclient/styles.html",
  },
  {
    name: "ImageSearchPlugin",
    version: "0.19",
    description: "Let LLMs find and show images from the web",
    docsPath: "smarter-resources/llmtool/plugin/image-search.html",
  },
  {
    name: "Infrastructure Manager",
    version: "0.18",
    description: "Manage and monitor your cloud infrastructure from the web console",
    docsPath: "smarter-framework/technologies/infrastructure.html",
  },
  {
    name: "Custom Domains",
    version: "0.18",
    description: "Serve LLMClients from your own branded domain, managed with a SAM manifest",
    docsPath: "smarter-resources/smarter-custom-domain.html",
  },
  {
    name: "Manifest Editor",
    version: "0.17",
    description: "Edit, validate, save, clone and delete manifests in the web console",
    docsPath: "smarter-platform/smarter-web-console.html",
  },
  {
    name: "Budgets",
    version: "0.16",
    description: "Enforce spending limits on any resource, with budget vs actual charts",
    docsPath: "smarter-resources/smarter-budget.html",
  },
  {
    name: "LLMHosts",
    version: "0.16",
    description: "Run open-weight LLMs on your own Kubernetes cluster",
    docsPath: "smarter-resources/smarter-llmhost.html",
  },
  {
    name: "Proxies",
    version: "0.16",
    description: "Pass requests through to LLM provider APIs, with keys kept as Smarter Secrets",
    docsPath: "smarter-resources/smarter-proxy.html",
  },
  {
    name: "VectorStores",
    version: "0.16",
    description: "Manage RAG vector databases: self-hosted Qdrant, Qdrant Cloud and Pinecone",
    docsPath: "smarter-resources/smarter-vectorstore.html",
  },
];

function WhatsNew() {
  return (
    <>
      {/* begin::What's New widget */}
      <section id="whats-new" aria-label="What's New" className="card border-transparent h-xl-100">
        {/* begin::Header */}
        <div className="card-header border-0 pt-5">
          <h3 className="card-title align-items-start flex-column">
            <span className="card-label fw-bold text-gray-900">What's New</span>
            <span className="text-muted mt-1 fw-semibold fs-7">Recently added Smarter features</span>
          </h3>
        </div>
        {/* end::Header */}
        {/* begin::Body */}
        <div className="card-body pt-3">
          <ul className="whats-new-list list-unstyled row g-4 mb-0">
            {FEATURES.map((feature) => (
              <li key={feature.name} className="col-md-6 d-flex align-items-start">
                <span className="badge badge-light-primary fw-bold me-3 mt-1">{feature.version}</span>
                <div>
                  <a
                    href={`${DOCS_BASE_URL}/${feature.docsPath}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-gray-900 text-hover-primary fw-bold fs-6"
                  >
                    {feature.name}
                  </a>
                  <div className="text-gray-600 fs-7">{feature.description}</div>
                </div>
              </li>
            ))}
          </ul>
        </div>
        {/* end::Body */}
      </section>
      {/* end::What's New widget */}
    </>
  );
}

export default WhatsNew;

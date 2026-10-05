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
import "./styles.css";

interface Feature {
  name: string;
  version: string;
  description: string;
  docsPath: string;
}

const DOCS_BASE_URL = "https://docs.smarter.sh";

const FEATURES: Feature[] = [
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
  {
    name: "WebsearchPlugin",
    version: "0.16",
    description: "Let LLMs search the web using services like Tavily",
    docsPath: "smarter-resources/plugin/plugin/websearch.html",
  },
  {
    name: "Guardrails",
    version: "0.15",
    description: "Manifest-declared guardrails that screen LLM prompts",
    docsPath: "smarter-resources/smarter-guardrail.html",
  },
  {
    name: "MCPClient",
    version: "0.15",
    description: "Connect LLMs to remote Model Context Protocol servers",
    docsPath: "smarter-resources/smarter-mcpclient.html",
  },
  {
    name: "SkillPlugin",
    version: "0.15",
    description: "Agent Skills (SKILL.md), inline or sourced from GitHub",
    docsPath: "smarter-resources/plugin/plugin/skill.html",
  },
];

function WhatsNew() {
  return (
    <>
      {/* begin::What's New widget */}
      <section id="whats-new" aria-label="WhatsNew" className="card border-transparent h-xl-100">
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

/**
 * The tab's introduction, for a reader who is new to Smarter: what a SAM resource is, that each is declared in a
 * manifest, which can be edited in the web console, and that an LLMClient is built from a tree of them.
 */
import type { ReactNode } from "react";
import { gettext } from "@smarter/common";

import { DOCS_URLS } from "../lib/const";

function DocsLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <a href={href} target="_blank" rel="noopener noreferrer" className="fw-semibold text-warning">
      {children}
      <i className="ki-outline ki-arrow-up-right fs-8 ms-1" aria-hidden="true" />
    </a>
  );
}

interface ConceptProps {
  icon: string;
  title: string;
  children: ReactNode;
  links: ReactNode;
}

function Concept({ icon, title, children, links }: ConceptProps) {
  return (
    <section className="architecture-concept col-12 col-xl-4">
      <div className="architecture-concept-card d-flex flex-column h-100 p-6">
        <div className="d-flex align-items-center mb-3">
          <span className="architecture-concept-icon me-3" aria-hidden="true">
            <i className={`ki-outline ki-${icon} fs-2`} />
          </span>
          <h3 className="fs-6 fw-bold text-white mb-0">{title}</h3>
        </div>
        <p className="architecture-hero-lead fs-7 mb-4 flex-grow-1">{children}</p>
        <div className="d-flex flex-wrap gap-4 fs-7">{links}</div>
      </div>
    </section>
  );
}

export default function Introduction() {
  return (
    <header className="architecture-introduction architecture-hero">
      <div className="architecture-kicker fw-bold fs-7 mb-3">{gettext("Architecture")}</div>
      <h2 className="fs-2hx fw-bolder text-white mb-3">{gettext("How this LLMClient is built")}</h2>
      <p className="architecture-hero-lead fs-5 mw-750px mb-8">
        {gettext(
          "An LLMClient is a sophisticated solution, built artisanally from a hierarchical tree of SAM resources. This is its tree: each card is a resource that it uses, directly or through another resource.",
        )}
      </p>
      <div className="row g-5">
        <Concept
          icon="abstract-26"
          // Translators: SAM is the Smarter Application Manifest, a product name.
          title={gettext("Everything is a SAM resource")}
          links={<DocsLink href={DOCS_URLS.manifests}>{gettext("Smarter Application Manifests")}</DocsLink>}
        >
          {gettext(
            "LLMClients, Providers, plugins, Connections, Secrets and Guardrails are all SAM resources. Each is declared in a manifest, a short YAML document that says what the resource should be, and Smarter makes it so.",
          )}
        </Concept>
        <Concept
          icon="notepad-edit"
          title={gettext("Edit any manifest here")}
          links={<DocsLink href={DOCS_URLS.webConsole}>{gettext("The web console")}</DocsLink>}
        >
          {gettext(
            "Every manifest can be edited directly in the web console. Click a card to open its resource's manifest in a new tab, change it, and save it: Smarter applies it at once.",
          )}
        </Concept>
        <Concept
          icon="data"
          title={gettext("An LLMClient is a tree")}
          links={
            <>
              <DocsLink href={DOCS_URLS.llmclient}>{gettext("LLMClients")}</DocsLink>
              <DocsLink href={DOCS_URLS.dependencyTrees}>{gettext("Dependency trees")}</DocsLink>
            </>
          }
        >
          {gettext(
            "Its Provider supplies the LLM, its plugins and MCPClients give it tools, its Guardrails screen what goes in and out, and the Connections and Secrets beneath them reach your data, safely. A resource that two others use appears under each of them.",
          )}
        </Concept>
      </div>
    </header>
  );
}

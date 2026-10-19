/**
 * The sections of the page at a deployed LLMClient's url only: The Smarter Project, which built it, its
 * open source repositories, a notice for platform administrators, and the footer.
 */
import { gettext, interpolate } from "@smarter/common";

import Terminal from "./Terminal";
import { GITHUB_URLS } from "../lib/const";
import type { LLMClientDeploymentPage } from "../lib/types";

/** The waffle switch that serves the page. */
const SWITCH = "enable_llmclient_endpoints_page";

/** One of The Smarter Project's features. */
function Feature({ icon, title, text }: { icon: string; title: string; text: string }) {
  return (
    <div className="col-md-6 col-xl-3">
      <div className="card card-flush h-100 shadow-sm">
        <div className="card-body p-8">
          <span className="smarter-feature-icon mb-6" aria-hidden="true">
            <i className={`ki-outline ${icon} fs-2x`} />
          </span>
          <h3 className="fw-bold text-gray-900 mb-3">{title}</h3>
          <p className="text-gray-600 fs-6 mb-0">{text}</p>
        </div>
      </div>
    </div>
  );
}

/** One of The Smarter Project's repositories. */
function Repository({ href, name, text }: { href: string; name: string; text: string }) {
  return (
    <div className="col-sm-6">
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="d-block border border-gray-700 rounded p-5 h-100"
      >
        <div className="text-white fw-bold fs-5 mb-1">{name}</div>
        <div className="smarter-hero-lead fs-7">{text}</div>
      </a>
    </div>
  );
}

export default function SmarterProject({ page }: { page: LLMClientDeploymentPage }) {
  const { links, snippets } = page;
  return (
    <>
      <section className="py-15 py-lg-20">
        <div className="container-xxl">
          <div className="text-center mb-12">
            <div className="smarter-section-kicker fw-bold fs-7 mb-3">{gettext("The Smarter Project")}</div>
            <h2 className="fs-2hx fw-bolder text-gray-900 mb-4">{gettext("Build your own LLM applications")}</h2>
            <p className="fs-5 text-gray-600 mw-750px mx-auto">{links.productDescription}</p>
          </div>
          <div className="row g-8">
            <Feature
              icon="ki-message-programming"
              title={gettext("Prompt Engineer's Workbench")}
              text={gettext(
                "Write the system prompt, chat with the LLM, and watch every request, tool call and response as it happens.",
              )}
            />
            <Feature
              icon="ki-document"
              title={gettext("Declarative manifests")}
              text={gettext(
                "Every resource, from LLMClients to secrets, is a YAML manifest that you apply with the cli or the api.",
              )}
            />
            <Feature
              icon="ki-wrench"
              title={gettext("Tools for the LLM")}
              text={gettext(
                "Give an LLM your apis, databases and MCP servers, with plugins, extensions and MCP clients.",
              )}
            />
            <Feature
              icon="ki-technology-2"
              title={gettext("Your choice of LLM")}
              text={gettext("Switch the LLM provider and model with one line of the manifest.")}
            />
            <Feature
              icon="ki-rocket"
              title={gettext("One-command deploys")}
              text={gettext(
                "A deployed LLMClient gets its own host and TLS certificate, and can move to your own domain.",
              )}
            />
            <Feature
              icon="ki-code"
              title={gettext("Embed it anywhere")}
              text={gettext("Put the chat on any web page with Smarter Chat, the @smarter.sh/ui-chat React component.")}
            />
            <Feature
              icon="ki-shield-tick"
              title={gettext("Guardrails")}
              text={gettext(
                "Check prompts and responses, for example for personal data and prompt injection, before they reach the LLM or the user.",
              )}
            />
            <Feature
              icon="ki-abstract-26"
              title={gettext("Cli and SDKs")}
              text={gettext("Script everything with the smarter cli, and the Python, Node.js and Go SDKs.")}
            />
          </div>
        </div>
      </section>

      <section className="pb-15 pb-lg-20">
        <div className="container-xxl">
          <div className="card smarter-hero border-0 overflow-hidden">
            <div className="card-body p-10 p-lg-15">
              <div className="row g-10 align-items-center">
                <div className="col-lg-6">
                  <div className="smarter-section-kicker fw-bold fs-7 mb-3">{gettext("Open source")}</div>
                  <h2 className="text-white fs-2hx fw-bolder mb-5">{gettext("Free, open source, and yours to run")}</h2>
                  <p className="smarter-hero-lead fs-5 mb-8">
                    {gettext(
                      "The Smarter Project is open source software, licensed under the GNU Affero General Public License v3.0. Read the code, run it on your own Kubernetes cluster, and contribute on GitHub.",
                    )}
                  </p>
                  <div className="d-flex flex-wrap gap-3">
                    <a
                      href={GITHUB_URLS.organization}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn btn-primary fw-bold"
                    >
                      <i className="ki-outline ki-github fs-3" aria-hidden="true" />
                      github.com/smarter-sh
                    </a>
                    <a
                      href={links.marketingSiteUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn btn-light fw-bold"
                    >
                      <i className="ki-outline ki-home fs-3" aria-hidden="true" />
                      smarter.sh
                    </a>
                    <a href={links.docsUrl} target="_blank" rel="noopener noreferrer" className="btn btn-light fw-bold">
                      <i className="ki-outline ki-book-open fs-3" aria-hidden="true" />
                      docs.smarter.sh
                    </a>
                  </div>
                </div>
                <div className="col-lg-6">
                  <div className="row g-4">
                    <Repository
                      href={GITHUB_URLS.smarter}
                      name="smarter"
                      text={gettext("The platform: Django, Celery and the web console.")}
                    />
                    <Repository
                      href={GITHUB_URLS.cli}
                      name="smarter-cli"
                      text={gettext("Apply, describe and deploy manifests.")}
                    />
                    <Repository
                      href={GITHUB_URLS.chat}
                      name="smarter-chat"
                      text={gettext("The chat React component, on npm as @smarter.sh/ui-chat.")}
                    />
                    <Repository
                      href={GITHUB_URLS.python}
                      name="smarter-python"
                      text={gettext("The Python SDK. Node.js and Go SDKs too.")}
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="pb-12">
        <div className="container-xxl">
          <div className="notice d-flex bg-light-warning rounded border-warning border border-dashed p-6">
            <i className="ki-outline ki-information fs-2tx text-warning me-4" aria-hidden="true" />
            <div className="flex-grow-1 min-w-0">
              <h2 className="text-gray-900 fw-bold fs-4 mb-2">{gettext("For platform administrators")}</h2>
              <div className="fs-6 text-gray-700 mb-4">
                {interpolate(
                  gettext(
                    "This page is meant for configuring a front end before it goes into production. Turn it off before you go live. It is served while the %(switch)s waffle switch is active. Turn the switch off, in the Django admin under Waffle, Switches, or with this command, and a browser's GET of these endpoints is answered 405 Method Not Allowed again. The api is unaffected.",
                  ),
                  { switch: SWITCH },
                )}
              </div>
              <Terminal title="bash" code={snippets.switchCommand} />
            </div>
          </div>
        </div>
      </section>

      <footer className="border-top py-8">
        <div className="container-xxl d-flex flex-column flex-md-row align-items-center justify-content-between gap-3">
          <a
            href={links.marketingSiteUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="d-flex align-items-center gap-3 text-gray-700 text-hover-primary"
          >
            <img alt="" src={links.logoUrl} className="h-30px" />
            <span className="fw-semibold">{links.productName}</span>
          </a>
          <div className="d-flex gap-6 fs-6">
            <a
              href={links.marketingSiteUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-gray-600 text-hover-primary"
            >
              smarter.sh
            </a>
            <a
              href={links.docsUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-gray-600 text-hover-primary"
            >
              {gettext("Docs")}
            </a>
            <a
              href={GITHUB_URLS.organization}
              target="_blank"
              rel="noopener noreferrer"
              className="text-gray-600 text-hover-primary"
            >
              GitHub
            </a>
          </div>
        </div>
      </footer>
    </>
  );
}

/** The workbench's note, at the bottom of its tab, about the page at the deployed LLMClient's url. */
export function EndpointsPageNote() {
  return (
    <section className="pb-12">
      <div className="container-xxl">
        <div className="d-flex align-items-start text-gray-600 fs-7">
          <i className="ki-outline ki-information fs-3 text-gray-500 me-3" aria-hidden="true" />
          <div>
            {interpolate(
              gettext(
                "A browser that opens the LLMClient's url sees this page too, while a platform administrator has turned on the %(switch)s waffle switch. Otherwise, a browser's GET of the url is answered 405 Method Not Allowed, because it is an api. This tab is always here.",
              ),
              { switch: SWITCH },
            )}
          </div>
        </div>
      </div>
    </section>
  );
}

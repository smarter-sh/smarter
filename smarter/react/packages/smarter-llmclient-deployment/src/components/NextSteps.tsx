/**
 * "Where to go from here?": the integrations that put the LLMClient's chat on a web site, the origin
 * that each needs allowed in its manifest, and, in the workbench, how a user who may not change the
 * LLMClient can clone it.
 */
import type { ReactNode } from "react";
import { gettext, interpolate, interpolateNodes } from "@smarter/common";

import Terminal from "./Terminal";
import { DOCS_URLS, GITHUB_URLS, NPM_PACKAGE_URL } from "../lib/const";
import type { DeploymentOwnership, LLMClientDeploymentPage } from "../lib/types";

/** A user who may not change the LLMClient: leave it as it is, or clone it. Workbench only. */
function NotYoursNotice({ name, ownership }: { name: string; ownership: DeploymentOwnership }) {
  return (
    <section
      aria-labelledby="not-yours-title"
      className="notice bg-light-warning rounded border-warning border border-dashed p-6 mb-10"
    >
      <h3 id="not-yours-title" className="text-gray-900 fw-bold mb-3">
        <i className="ki-outline ki-information fs-2 text-warning me-2" aria-hidden="true" />
        {gettext("This LLMClient isn't yours")}
      </h3>
      <p className="fs-6 text-gray-700 mb-4">
        {interpolateNodes(
          gettext(
            "%(name)s belongs to %(owner)s, who shares it with you. You can chat with it, read its manifest and use everything on this page that only reads it, but only its owner, or an admin of its account, can change it, deploy it or attach an api key to it. That leaves you two choices.",
          ),
          { name: <strong>{name}</strong>, owner: <strong>{ownership.owner}</strong> },
        )}
      </p>
      <div className="row g-6 mb-4">
        <div className="col-lg-5">
          <h4 className="text-gray-900 fw-bold fs-5 mb-2">{gettext("1. Leave it as it is")}</h4>
          <p className="fs-6 text-gray-700 mb-0">
            {gettext(
              "Use it as an example. Chat with it, read its manifest, and borrow whatever you like for LLMClients of your own. Nothing that you do here changes it.",
            )}
          </p>
        </div>
        <div className="col-lg-7">
          <h4 className="text-gray-900 fw-bold fs-5 mb-2">{gettext("2. Clone it, and work on your copy")}</h4>
          <p className="fs-6 text-gray-700 mb-3">
            {gettext(
              "A clone is a new LLMClient, owned by you, that starts as an exact copy of this one: the same instructions, LLM provider and model, and the same plugins, MCP clients and guardrails, except any that you aren't allowed to use. It has its own name, and its own url. From then on the two are independent: your changes to the copy never touch the original, and later changes to the original never reach your copy.",
            )}
          </p>
          <ol className="fs-6 text-gray-700 ps-5 mb-0">
            <li className="mb-1">
              {interpolateNodes(gettext("Open the %(list)s list, and its %(tab)s tab."), {
                list: (
                  <a href={ownership.llmclientListUrl} target="_top" className="fw-semibold">
                    {gettext("LLM Clients")}
                  </a>
                ),
                tab: <strong>{gettext("Shared LLM Clients")}</strong>,
              })}
            </li>
            <li className="mb-1">
              {interpolateNodes(
                gettext("Find %(name)s, and click its %(clone)s button, the green icon of two pages."),
                {
                  name: <strong>{name}</strong>,
                  clone: <strong>{gettext("Clone")}</strong>,
                },
              )}
            </li>
            <li className="mb-1">
              {interpolateNodes(
                gettext(
                  "Type a name for your copy, and click %(ok)s. Smarter writes the name in snake case: %(example)s becomes %(snake_case)s.",
                ),
                {
                  ok: <strong>{gettext("OK")}</strong>,
                  example: <em>My Advisor</em>,
                  snake_case: <code>my_advisor</code>,
                },
              )}
            </li>
            <li>
              {interpolateNodes(
                gettext(
                  "Your copy appears in the %(your_tab)s tab, under its new name, and the original stays in %(shared_tab)s, unchanged. Open your copy in the workbench, and from there edit its manifest, deploy it, and put it on your site, as this page describes.",
                ),
                {
                  your_tab: <strong>{gettext("Your LLM Clients")}</strong>,
                  shared_tab: <strong>{gettext("Shared LLM Clients")}</strong>,
                },
              )}
            </li>
          </ol>
        </div>
      </div>
      <p className="fs-7 text-gray-600 mb-0">
        <a href={ownership.ownershipDocsUrl} target="_blank" rel="noopener noreferrer" className="fw-semibold">
          {gettext("How ownership of Smarter resources works")}
        </a>
        {": "}
        {gettext("who owns a resource, who can read it, and who can change it.")}
      </p>
    </section>
  );
}

/** A link button of an integration's card. */
function CardLink({
  href,
  icon,
  primary = false,
  children,
}: {
  href: string;
  icon: string;
  primary?: boolean;
  children: ReactNode;
}) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className={`btn btn-sm ${primary ? "btn-light-primary" : "btn-light"} fw-bold`}
    >
      <i className={`${icon} fs-4`} aria-hidden="true" />
      {children}
    </a>
  );
}

/** An integration's card: its brand's icon, its name, how to install it, and its links. */
function IntegrationCard({
  brand,
  icon,
  title,
  wide = false,
  children,
}: {
  brand: string;
  icon: string;
  title: string;
  wide?: boolean;
  children: ReactNode;
}) {
  return (
    <div className={wide ? "col-xl-6" : "col-md-6 col-xl-4"}>
      <div className="card card-flush h-100 shadow-sm">
        <div className="card-body p-8 d-flex flex-column">
          <span className={`smarter-integration-icon smarter-integration-${brand} mb-6`} aria-hidden="true">
            <i className={`fa-brands ${icon} fs-2x`} />
          </span>
          <h3 className="fw-bold text-gray-900 mb-3">{title}</h3>
          {children}
        </div>
      </div>
    </div>
  );
}

export default function NextSteps({ page }: { page: LLMClientDeploymentPage }) {
  const { llmclient, snippets, ownership, mode } = page;
  return (
    <section id="next" className={mode === "public" ? "py-15 py-lg-20" : "py-12"}>
      <div className="container-xxl">
        <div className="text-center mb-10">
          <div className="smarter-section-kicker fw-bold fs-7 mb-3">{gettext("Your next step")}</div>
          <h2 className="fs-2hx fw-bolder text-gray-900 mb-4">{gettext("Where to go from here?")}</h2>
          <p className="fs-5 text-gray-600 mw-750px mx-auto">
            {interpolate(
              gettext(
                "Put %(app_name)s in front of people. Smarter Chat works on any web site, and these integrations are ready to use: pick the one that matches yours. Each of them needs only this LLMClient's url.",
              ),
              { app_name: llmclient.appName },
            )}
          </p>
        </div>

        {ownership && !ownership.canEdit && <NotYoursNotice name={llmclient.name} ownership={ownership} />}

        <div className="notice d-flex flex-column flex-lg-row bg-light-primary rounded border-primary border border-dashed p-6 mb-10 gap-6">
          <div className="flex-grow-1 min-w-0">
            <h3 className="text-gray-900 fw-bold mb-2">
              <i className="ki-outline ki-shield-tick fs-2 text-primary me-2" aria-hidden="true" />
              {gettext("First, allow your site's origin")}
            </h3>
            <p className="fs-6 text-gray-700 mb-0">
              {interpolateNodes(
                gettext(
                  "Browsers let a page call this url only if the LLMClient's manifest lists the page's origin: its scheme, host and port, without a path. Add your site, and your development server if you have one, then apply the manifest again, in the workbench's Manifest tab or with %(command)s. Skip this, and the chat fails in the browser with a CORS error.",
                ),
                { command: <code>smarter apply</code> },
              )}
            </p>
          </div>
          <div className="smarter-notice-code min-w-0">
            <Terminal title="manifest.yaml" code={snippets.allowedOriginsYaml} />
          </div>
        </div>

        <div className="row g-8">
          <IntegrationCard brand="wordpress" icon="fa-wordpress" title="WordPress">
            <p className="text-gray-600 fs-6 mb-5">
              {gettext(
                "A plugin: a chat launcher on every page, a Smarter Chat block, and a [smarter_chat] shortcode.",
              )}
            </p>
            <ol className="text-gray-700 fs-6 ps-5 mb-6 flex-grow-1">
              <li className="mb-2">
                {gettext(
                  "Download smarter-chat-<version>.zip from the plugin's latest release, and upload it in Plugins, Add New, Upload Plugin.",
                )}
              </li>
              <li>{gettext("In Settings, Smarter Chat, enter this LLMClient's url.")}</li>
            </ol>
            <div className="d-flex flex-wrap gap-2">
              <CardLink href={GITHUB_URLS.wordpressReleases} icon="ki-outline ki-cloud-download" primary>
                {gettext("Download")}
              </CardLink>
              <CardLink href={DOCS_URLS.wordpress} icon="ki-outline ki-book-open">
                {gettext("Guide")}
              </CardLink>
            </div>
          </IntegrationCard>
          <IntegrationCard brand="drupal" icon="fa-drupal" title="Drupal">
            <p className="text-gray-600 fs-6 mb-5">
              {gettext(
                "A module for Drupal 10.3 and 11: a chat launcher on every page, and a Smarter Chat block for any region.",
              )}
            </p>
            <div className="mb-5">
              <Terminal title="bash" code={snippets.drupalInstallCommands} />
            </div>
            <p className="text-gray-700 fs-6 mb-6 flex-grow-1">
              {gettext("Then, in Configuration, Web services, Smarter Chat, enter this LLMClient's url.")}
            </p>
            <div className="d-flex flex-wrap gap-2">
              <CardLink href={GITHUB_URLS.drupal} icon="ki-outline ki-github" primary>
                GitHub
              </CardLink>
              <CardLink href={DOCS_URLS.drupal} icon="ki-outline ki-book-open">
                {gettext("Guide")}
              </CardLink>
            </div>
          </IntegrationCard>
          <IntegrationCard brand="shopify" icon="fa-shopify" title="Shopify">
            <p className="text-gray-600 fs-6 mb-5">
              {gettext(
                "A theme app extension: a chat launcher on every page, and a Smarter Chat block for any section.",
              )}
            </p>
            <ol className="text-gray-700 fs-6 ps-5 mb-6 flex-grow-1">
              <li className="mb-2">
                {gettext(
                  "Deploy the extension as your store's own app, from a Shopify Partner account, and install it on your store.",
                )}
              </li>
              <li className="mb-2">
                {gettext(
                  "In the theme editor, turn on App embeds, Smarter Chat launcher, and enter this LLMClient's url.",
                )}
              </li>
              <li>{gettext("Allow both of your store's origins: its myshopify.com domain, and its own domain.")}</li>
            </ol>
            <div className="d-flex flex-wrap gap-2">
              <CardLink href={GITHUB_URLS.shopify} icon="ki-outline ki-github" primary>
                GitHub
              </CardLink>
              <CardLink href={DOCS_URLS.shopify} icon="ki-outline ki-book-open">
                {gettext("Guide")}
              </CardLink>
            </div>
          </IntegrationCard>
          <IntegrationCard brand="react" icon="fa-react" title={gettext("React, from npm")} wide>
            <p className="text-gray-600 fs-6 mb-5">
              {interpolateNodes(
                gettext(
                  "%(package)s, the component that the workbench uses, for a React 19 application built with Vite, webpack or Next.js.",
                ),
                { package: <code>@smarter.sh/ui-chat</code> },
              )}
            </p>
            <div className="mb-4">
              <Terminal title="bash" code={snippets.npmInstallCommand} />
            </div>
            <div className="mb-6 flex-grow-1">
              <Terminal title="Chat.tsx" code={snippets.reactSnippet} />
            </div>
            <div className="d-flex flex-wrap gap-2">
              <CardLink href={NPM_PACKAGE_URL} icon="fa-brands fa-npm" primary>
                npm
              </CardLink>
              <CardLink href={DOCS_URLS.reactInstallation} icon="ki-outline ki-book-open">
                {gettext("Guide")}
              </CardLink>
            </div>
          </IntegrationCard>
          <IntegrationCard brand="html" icon="fa-html5" title={gettext("Any web page, in html")} wide>
            <p className="text-gray-600 fs-6 mb-5">
              {gettext(
                "One script tag, with no build: for a static site, a server-rendered page, Squarespace, Wix or Webflow. Paste it before </body>, and a chat button appears in a corner of the page.",
              )}
            </p>
            <div className="mb-5">
              <Terminal title="index.html" code={snippets.embedHtml} />
            </div>
            <p className="text-gray-700 fs-6 mb-6 flex-grow-1">
              {interpolateNodes(
                gettext(
                  "The chat renders in its own Shadow DOM, so your site's css can't break it. To put it inside the page instead of a launcher, add %(element)s where it goes.",
                ),
                { element: <code>{'<smarter-chat chatbot="…"></smarter-chat>'}</code> },
              )}
            </p>
            <div className="d-flex flex-wrap gap-2">
              <CardLink href={DOCS_URLS.embedScript} icon="ki-outline ki-book-open">
                {gettext("Guide")}
              </CardLink>
            </div>
          </IntegrationCard>
        </div>

        <div className="d-flex flex-column flex-md-row align-items-md-center gap-4 border border-dashed border-gray-300 rounded p-6 mt-8">
          <i className="ki-outline ki-element-11 fs-2tx text-gray-500" aria-hidden="true" />
          <div className="flex-grow-1 fs-6 text-gray-700">
            <span className="fw-bold text-gray-900">{gettext("Something else?")}</span>{" "}
            {gettext(
              "Google Tag Manager, and documentation sites built with Docusaurus, MkDocs, Sphinx or VitePress, have integrations too. Or build your own front end on this url's api, below, or with the Python, Node.js and Go SDKs.",
            )}
          </div>
          <div className="d-flex flex-wrap gap-2">
            <a href={DOCS_URLS.gtm} target="_blank" rel="noopener noreferrer" className="btn btn-sm btn-light fw-bold">
              Google Tag Manager
            </a>
            <a
              href={DOCS_URLS.docsSites}
              target="_blank"
              rel="noopener noreferrer"
              className="btn btn-sm btn-light fw-bold"
            >
              {gettext("Docs sites")}
            </a>
            <a href={DOCS_URLS.sdks} target="_blank" rel="noopener noreferrer" className="btn btn-sm btn-light fw-bold">
              {gettext("SDKs")}
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}

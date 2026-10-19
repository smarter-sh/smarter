/**
 * "Need to secure this url?": how to require an api key, and give it to a front end. The workbench
 * manages the LLMClient's api key in place; the page at the deployed LLMClient's url explains the
 * commands and the manifest that do it.
 */
import type { ReactNode } from "react";
import { gettext, interpolateNodes, type SessionContext } from "@smarter/common";

import ApiKeys from "./ApiKeys";
import Terminal from "./Terminal";
import { DOCS_URLS } from "../lib/const";
import type { LLMClientDeploymentPage } from "../lib/types";

/** A numbered step's heading. */
function Step({ step, title }: { step: number; title: string }) {
  return (
    <div className="d-flex align-items-center mb-4">
      <span className="smarter-step me-3">{step}</span>
      <h3 className="fw-bold text-gray-900 mb-0">{title}</h3>
    </div>
  );
}

/** How a front end sends an LLMClient's api key: Smarter Chat's data-api-key and apiKey. */
function ApiKeyUsage({ step, page }: { step: number; page: LLMClientDeploymentPage }) {
  return (
    <>
      <Step step={step} title={gettext("Give it to Smarter Chat")} />
      <p className="text-gray-600 fs-6 mb-5">
        {interpolateNodes(
          gettext(
            "Smarter Chat sends the key with every request, as %(header)s. The WordPress, Drupal and Shopify integrations have an api key setting. In html, add %(attribute)s:",
          ),
          { header: <code>{"Authorization: Token <key>"}</code>, attribute: <code>data-api-key</code> },
        )}
      </p>
      <div className="mb-5">
        <Terminal title="index.html" code={page.snippets.embedHtmlWithApiKey} />
      </div>
      <p className="text-gray-600 fs-6 mb-5">
        {gettext("In React, pass apiKey, from your build's environment rather than from your source code:")}
      </p>
      <Terminal title="Chat.tsx" code={page.snippets.reactSnippetWithApiKey} />
    </>
  );
}

/** The steps of the page at the deployed LLMClient's url: create a key, attach it, give it to Smarter Chat. */
function PublicSteps({ page }: { page: LLMClientDeploymentPage }) {
  const { snippets, links } = page;
  return (
    <div className="row g-8">
      <div className="col-xl-4">
        <Step step={1} title={gettext("Create an api key")} />
        <p className="text-gray-600 fs-6 mb-5">
          {gettext(
            "An api key belongs to a staff user of your account, and a platform administrator creates it with this command. The command prints the key's name, and its secret, once: store the secret somewhere safe, such as a password manager or your hosting's secrets.",
          )}
        </p>
        <div className="mb-5">
          <Terminal title="bash" code={snippets.createApiKeyCommand} />
        </div>
        <p className="text-gray-600 fs-6 mb-0">
          {gettext("The web console's API Keys page lists your keys, and turns a key off without deleting it.")}{" "}
          <a href={links.apiKeysUrl} className="fw-semibold">
            {gettext("API Keys")}
          </a>
        </p>
      </div>
      <div className="col-xl-4">
        <Step step={2} title={gettext("Attach it to this LLMClient")} />
        <p className="text-gray-600 fs-6 mb-5">
          {interpolateNodes(
            gettext(
              "Name the key in the LLMClient's manifest, and apply the manifest again, in the workbench's Manifest tab or with %(command)s. From then on, every request to the url needs the key, and this page says \"Api key required\".",
            ),
            { command: <code>smarter apply</code> },
          )}
        </p>
        <div className="mb-5">
          <Terminal title="manifest.yaml" code={snippets.apiKeyYaml} />
        </div>
        <p className="text-gray-600 fs-6 mb-0">
          {gettext(
            "To replace a key, create a new one, name it in the manifest instead, and apply it: Smarter detaches the old key. Then turn the old key off.",
          )}
        </p>
      </div>
      <div className="col-xl-4">
        <ApiKeyUsage step={3} page={page} />
      </div>
    </div>
  );
}

/** A link to the docs, in a notice. */
function DocsLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <a href={href} target="_blank" rel="noopener noreferrer" className="fw-semibold">
      {children}
    </a>
  );
}

interface SecureUrlProps {
  page: LLMClientDeploymentPage;
  /** The workbench's session, for its api key actions. */
  session: SessionContext | null;
  onPage: (page: LLMClientDeploymentPage) => void;
}

export default function SecureUrl({ page, session, onPage }: SecureUrlProps) {
  const { authenticated, mode, apiKeys, snippets, links } = page;
  const workbench = mode === "workbench" && apiKeys && session;
  return (
    <section id="secure" className={`${mode === "public" ? "py-15 py-lg-20" : "py-12"} border-top`}>
      <div className="container-xxl">
        <div className="text-center mb-12">
          <div className="smarter-section-kicker fw-bold fs-7 mb-3">{gettext("Api keys")}</div>
          <h2 className="fs-2hx fw-bolder text-gray-900 mb-4">{gettext("Need to secure this url?")}</h2>
          <p className="fs-5 text-gray-600 mw-750px mx-auto">
            {authenticated
              ? gettext(
                  "This LLMClient already requires an api key: the url answers only requests that carry one of its keys. Here is how to give a key to a front end in production, and how to replace one.",
                )
              : gettext(
                  "Right now, anyone who has this url can chat with it, and every prompt is charged to its owner. Attach an api key, and the url answers only requests that carry it. The workbench keeps working, with your login.",
                )}
            {workbench && <> {gettext("You can do it right here.")}</>}
          </p>
        </div>
        {workbench ? (
          <div className="row g-8">
            <div className="col-xl-8">
              <ApiKeys
                apiKeys={apiKeys}
                createApiKeyCommand={snippets.createApiKeyCommand}
                apiKeysUrl={links.apiKeysUrl}
                session={session}
                onPage={onPage}
              />
            </div>
            <div className="col-xl-4">
              <ApiKeyUsage step={2} page={page} />
            </div>
          </div>
        ) : (
          <PublicSteps page={page} />
        )}
        <div className="notice d-flex bg-light-warning rounded border-warning border border-dashed p-6 mt-10">
          <i className="ki-outline ki-shield-cross fs-2tx text-warning me-4" aria-hidden="true" />
          <div className="flex-grow-1 min-w-0 fs-6 text-gray-700">
            <h3 className="text-gray-900 fw-bold fs-4 mb-2">{gettext("A key in a web page is not a secret")}</h3>
            <p className="mb-3">
              {gettext(
                "Anyone who opens the page can read the key in its source, and use it from anywhere. On a public site, a key limits who can call the url, rather than hiding it, so combine it with the rest:",
              )}
            </p>
            <ul className="mb-3">
              <li>{gettext("give each site a key of its own, and turn it off if it is abused;")}</li>
              <li>{gettext("list only your site's origins in allowedOrigins, which browsers enforce;")}</li>
              <li>{gettext("give the LLMClient a budget, which caps what its prompts can cost.")}</li>
            </ul>
            <p className="mb-0">
              {gettext(
                "For an internal tool, or a server-to-server integration, keep the key on your server, and call this url from there.",
              )}{" "}
              <DocsLink href={DOCS_URLS.apiKeys}>{gettext("Api keys")}</DocsLink>
              {" · "}
              <DocsLink href={DOCS_URLS.budgets}>{gettext("Budgets")}</DocsLink>
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

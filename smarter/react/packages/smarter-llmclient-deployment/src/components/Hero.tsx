/**
 * The top of the page: the LLMClient's status and url, the command that deploys it if it isn't
 * deployed, the links to the page's sections, and a card about the LLMClient.
 */
import { gettext, interpolate, interpolateNodes } from "@smarter/common";

import CopyButton from "./CopyButton";
import Terminal from "./Terminal";
import { DOCS_URLS } from "../lib/const";
import type { LLMClientDeploymentPage } from "../lib/types";

/** The LLMClient's card: its name, owner (in the workbench only), status, LLM and access. */
function LLMClientCard({ page }: { page: LLMClientDeploymentPage }) {
  const { llmclient, deployed, authenticated, ownership } = page;
  const rows: [string, string][] = [[gettext("Name"), llmclient.name]];
  if (ownership) rows.push([gettext("Owner"), ownership.owner]);
  rows.push([gettext("Status"), deployed ? gettext("Deployed") : gettext("Not deployed")]);
  if (llmclient.provider) rows.push([gettext("LLM provider"), llmclient.provider]);
  if (llmclient.model) rows.push([gettext("Model"), llmclient.model]);
  if (llmclient.version) rows.push([gettext("Version"), llmclient.version]);
  rows.push([gettext("Access"), authenticated ? gettext("Api key required") : gettext("Public")]);
  return (
    <div className="card bg-transparent border border-gray-700">
      <div className="card-body p-8">
        <h2 className="text-gray-500 fs-7 fw-bold text-uppercase mb-5">{gettext("This LLMClient")}</h2>
        <table className="table table-borderless align-middle mb-0">
          <tbody className="fs-6">
            {rows.map(([label, value]) => (
              <tr key={label}>
                <th scope="row" className="text-gray-500 fw-normal ps-0">
                  {label}
                </th>
                <td className="text-white fw-semibold text-end pe-0">{value}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="smarter-hero-lead fs-7 mt-5">
          {authenticated
            ? gettext(
                "Every request needs one of this LLMClient's api keys. A key that is in a web page is public: give each site a key of its own, and revoke it if it is abused.",
              )
            : gettext(
                "Anyone who has this url can chat with it, and every prompt is charged to its owner. Attach an api key to require one, or give it a budget.",
              )}{" "}
          <a href="#secure" className="text-warning">
            {gettext("Need to secure this url?")}
          </a>
          {!authenticated && (
            <>
              {" · "}
              <a href={DOCS_URLS.budgets} target="_blank" rel="noopener noreferrer" className="text-warning">
                {gettext("Budgets")}
              </a>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default function Hero({ page }: { page: LLMClientDeploymentPage }) {
  const { llmclient, deployed, mode, links, snippets } = page;
  const isPublic = mode === "public";
  const appName = llmclient.appName;
  return (
    <section className={`smarter-hero ${isPublic ? "py-15 py-lg-20" : "py-10"}`}>
      <div className="container-xxl">
        <div className="row align-items-center g-10">
          <div className="col-lg-7">
            {isPublic && (
              <a
                href={links.marketingSiteUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="d-inline-block smarter-logo-tile mb-10"
              >
                <img alt={links.productName} src={links.logoUrl} className="h-60px" />
              </a>
            )}
            <div className="mb-4">
              {deployed ? (
                <span className="badge badge-light-success fs-7 fw-bold me-2">{gettext("Live")}</span>
              ) : (
                <span className="badge badge-light-warning fs-7 fw-bold me-2">{gettext("Not deployed")}</span>
              )}
              <span className="badge badge-light fs-7 fw-bold">{appName}</span>
            </div>
            <h1 className="smarter-status-title text-white fw-bolder text-uppercase mb-5">
              {deployed ? (
                <>
                  <i className="ki-outline ki-double-check-circle text-success" aria-hidden="true" />
                  {gettext("Deployed")}
                </>
              ) : (
                <>
                  <i className="ki-outline ki-rocket text-warning" aria-hidden="true" />
                  {gettext("Not deployed yet")}
                </>
              )}
            </h1>
            <p className="smarter-hero-lead fs-3 fw-semibold mb-5">
              {deployed
                ? interpolate(
                    gettext(
                      "%(app_name)s is live. Its system prompt, its LLM and its tools now answer at its own url:",
                    ),
                    { app_name: appName },
                  )
                : interpolate(
                    gettext(
                      "%(app_name)s works here, in the workbench, but nobody else can reach it yet. Deploy it, and it gets its own url, with its own TLS certificate:",
                    ),
                    { app_name: appName },
                  )}
            </p>
            <div className="smarter-url d-flex align-items-center gap-3 mb-6">
              <i className="ki-outline ki-cloud fs-2 text-gray-500" aria-hidden="true" />
              <code className="flex-grow-1 text-break">{`${llmclient.url}/`}</code>
              <CopyButton text={`${llmclient.url}/`} />
            </div>
            {deployed ? (
              <p className="smarter-hero-lead fs-5 mb-8">
                {interpolateNodes(
                  gettext(
                    "This url is an api, not a web page. It is the backend of Smarter Chat, the chat window of the workbench, which is also the %(package)s npm package. Put Smarter Chat on a web page, point it at this url, and your visitors are talking to %(app_name)s.",
                  ),
                  { package: <code>@smarter.sh/ui-chat</code>, app_name: appName },
                )}
              </p>
            ) : (
              <>
                <p className="smarter-hero-lead fs-5 mb-4">{gettext("Deploy it with the smarter cli:")}</p>
                <div className="mb-4">
                  <Terminal title="smarter cli" code={snippets.deployCommand} />
                </div>
                <p className="smarter-hero-lead fs-6 mb-8">
                  {gettext(
                    "Smarter then creates its host and its TLS certificate, which can take a few minutes. Reopen this tab afterwards. Until then, here is what you'll be able to do with it.",
                  )}
                </p>
              </>
            )}
            <div className="d-flex flex-wrap gap-3">
              {isPublic && (
                <a href={llmclient.workbenchUrl} className="btn btn-primary fw-bold">
                  <i className="ki-outline ki-arrow-left fs-3" aria-hidden="true" />
                  {gettext("Back to the workbench")}
                </a>
              )}
              <a href="#next" className={`btn ${isPublic ? "btn-light" : "btn-primary"} fw-bold`}>
                <i className="ki-outline ki-rocket fs-3" aria-hidden="true" />
                {gettext("Where to go from here?")}
              </a>
              <a href="#api" className="btn btn-dark fw-bold border border-gray-600">
                <i className="ki-outline ki-code fs-3" aria-hidden="true" />
                {gettext("How this url works")}
              </a>
            </div>
          </div>
          <div className="col-lg-5">
            <LLMClientCard page={page} />
          </div>
        </div>
      </div>
    </section>
  );
}

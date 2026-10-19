/**
 * "How it was built": the LLMClient's manifest, highlighted, with the commands that apply and deploy it.
 */
import { gettext, interpolate } from "@smarter/common";

import Terminal from "./Terminal";
import { DOCS_URLS } from "../lib/const";
import type { LLMClientDeploymentPage } from "../lib/types";
import { highlightYaml } from "../lib/yaml";

/** The manifest's YAML, as lines of colored tokens. */
export function HighlightedYaml({ text }: { text: string }) {
  return (
    <>
      {highlightYaml(text).map((tokens, line) => (
        // the lines and their tokens are in a fixed order, and never move.
        <span key={line}>
          {line > 0 && "\n"}
          {tokens.map((token, index) =>
            token.kind === "plain" ? (
              token.text
            ) : (
              <span key={index} className={`yaml-${token.kind}`}>
                {token.text}
              </span>
            ),
          )}
        </span>
      ))}
    </>
  );
}

/** One of the three reasons to declare an LLMClient in YAML. */
function Benefit({ text }: { text: string }) {
  return (
    <li className="d-flex align-items-start">
      <i className="ki-outline ki-check-circle fs-2 text-success me-3 mt-1" aria-hidden="true" />
      <div className="fs-6 text-gray-700">{text}</div>
    </li>
  );
}

export default function ManifestSection({ page }: { page: LLMClientDeploymentPage }) {
  const { llmclient, snippets, manifestYaml, mode } = page;
  return (
    <section id="manifest" className={mode === "public" ? "py-15 py-lg-20" : "py-12"}>
      <div className="container-xxl">
        <div className="row g-10 align-items-start">
          <div className="col-lg-5">
            <div className="smarter-section-kicker fw-bold fs-7 mb-3">{gettext("How it was built")}</div>
            <h2 className="fs-2hx fw-bolder text-gray-900 mb-6">
              {gettext("Designed in the workbench. Declared in YAML.")}
            </h2>
            <p className="fs-5 text-gray-700 mb-6">
              {interpolate(
                gettext(
                  "%(app_name)s was designed, tested and debugged in the Prompt Engineer's Workbench of the Smarter web console, and is deployed from a manifest: a short YAML file that declares everything it is. Change the manifest, apply it, and the url answers with your changes.",
                ),
                { app_name: llmclient.appName },
              )}
            </p>
            <ul className="list-unstyled d-flex flex-column gap-5 mb-8">
              <Benefit
                text={gettext("Declarative: the manifest says what the LLMClient is, and Smarter makes it so.")}
              />
              <Benefit
                text={gettext(
                  "Version controlled: keep manifests in git, review them in pull requests, apply them from CI.",
                )}
              />
              <Benefit
                text={gettext("Two commands from a YAML file to a live api with its own host and TLS certificate.")}
              />
            </ul>
            <div className="mb-6">
              <Terminal title="smarter cli" code={snippets.deployCommands} />
            </div>
            {mode === "public" && (
              <a href={llmclient.workbenchUrl} className="btn btn-primary fw-bold me-2 mb-2">
                <i className="ki-outline ki-message-programming fs-3" aria-hidden="true" />
                {gettext("Open it in the workbench")}
              </a>
            )}
            <a
              href={DOCS_URLS.llmclient}
              target="_blank"
              rel="noopener noreferrer"
              className="btn btn-light fw-bold mb-2"
            >
              <i className="ki-outline ki-book-open fs-3" aria-hidden="true" />
              {gettext("LLMClient docs")}
            </a>
          </div>
          {manifestYaml && (
            <div className="col-lg-7">
              <Terminal title={`${llmclient.name}.yaml`} code={manifestYaml} tall>
                <HighlightedYaml text={manifestYaml} />
              </Terminal>
              <p className="text-gray-500 fs-7 mt-3 mb-0">
                {gettext(
                  "This LLMClient's manifest, as smarter describe llmclient returns it, without its owner's username. Its status is what Smarter reports about it, and is read-only.",
                )}
              </p>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

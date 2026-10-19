/**
 * The next steps, beneath the tree, for an LLMClient that is missing one of the three things that most LLMClients
 * have: a Guardrail, tools (a plugin, an Extension or an MCPClient), and styles. Each section explains the idea,
 * says where to browse what is available, and gives a manifest excerpt to paste into the LLMClient's manifest and
 * save. A section disappears once the LLMClient has what it suggests; with nothing missing, there is none.
 */
import type { ReactNode } from "react";
import { gettext, interpolateNodes } from "@smarter/common";

import ManifestSnippet from "./ManifestSnippet";
import { DOCS_URLS } from "../lib/const";
import {
  EXTENSION_SNIPPET,
  GUARDRAIL_SNIPPET,
  hasGuardrail,
  hasTools,
  MCPCLIENT_SNIPPET,
  PLUGIN_SNIPPET,
  STYLES_SNIPPET,
} from "../lib/gettingStarted";
import type { LLMClientArchitectureLinks, SAMDependencyTreeNode } from "../lib/types";

const code = (text: string) => <code className="architecture-inline-code">{text}</code>;

function DocsLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <a href={href} target="_blank" rel="noopener noreferrer" className="fw-semibold">
      <i className="ki-outline ki-book-open fs-6 me-1" aria-hidden="true" />
      {children}
      <i className="ki-outline ki-arrow-up-right fs-8 ms-1" aria-hidden="true" />
    </a>
  );
}

function BrowseLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <a href={href} target="_blank" rel="noopener noreferrer" className="btn btn-sm btn-light-primary">
      <i className="ki-outline ki-magnifier fs-5" aria-hidden="true" />
      {children}
    </a>
  );
}

interface StepsProps {
  /** The LLMClient's manifest page. */
  manifestUrl: string | null;
  /** Where in the manifest the excerpt goes, e.g. "Paste it on a new line beneath spec:". */
  where: ReactNode;
}

/** How to add an excerpt: open the manifest, paste it, save it. */
function Steps({ manifestUrl, where }: StepsProps) {
  const manifest = gettext("Open this LLMClient's manifest");
  return (
    <ol className="architecture-steps fs-7 text-gray-700 mb-5">
      <li>
        {manifestUrl ? (
          <a href={manifestUrl} target="_blank" rel="noopener noreferrer" className="fw-semibold">
            {manifest}
            <i className="ki-outline ki-exit-right-corner fs-8 ms-1" aria-hidden="true" />
          </a>
        ) : (
          manifest
        )}
        .
      </li>
      <li>
        {gettext("Click Copy on the example, and paste it into the manifest.")} {where}
      </li>
      <li>
        {gettext(
          "Click Save. Smarter applies the manifest at once. Then reload this tab, and the new resource appears in the tree.",
        )}
      </li>
    </ol>
  );
}

interface SuggestionProps {
  icon: string;
  title: string;
  children: ReactNode;
}

function Suggestion({ icon, title, children }: SuggestionProps) {
  const id = `architecture-suggestion-${icon}`;
  return (
    <section className="architecture-suggestion p-6 p-lg-8" aria-labelledby={id}>
      <div className="d-flex align-items-center mb-4">
        <span className="architecture-suggestion-icon me-4" aria-hidden="true">
          <i className={`ki-outline ki-${icon} fs-2`} />
        </span>
        <h3 id={id} className="fs-3 fw-bold text-gray-900 mb-0">
          {title}
        </h3>
      </div>
      {children}
    </section>
  );
}

interface ToolProps {
  title: string;
  description: string;
  choose: string;
  snippet: typeof PLUGIN_SNIPPET;
  caption: string;
  browse: ReactNode;
  docs: ReactNode;
}

/** One of the three ways to give an LLMClient tools, in a column. */
function Tool({ title, description, choose, snippet, caption, browse, docs }: ToolProps) {
  return (
    <div className="col-12 col-xl-4">
      <div className="architecture-tool d-flex flex-column h-100 p-5">
        <h4 className="fs-5 fw-bold text-gray-900 mb-2">{title}</h4>
        <p className="fs-7 text-gray-700 mb-2">{description}</p>
        <p className="fs-7 text-gray-700 mb-4">
          <span className="fw-semibold text-gray-900">{gettext("Choose it")}</span> {choose}
        </p>
        <div className="mt-auto">
          <ManifestSnippet snippet={snippet} label={title} />
          <p className="fs-8 text-gray-500 mt-2 mb-4">{caption}</p>
          <div className="d-flex flex-wrap align-items-center gap-4 fs-7">
            {browse}
            {docs}
          </div>
        </div>
      </div>
    </div>
  );
}

interface GettingStartedProps {
  tree: SAMDependencyTreeNode;
  styled: boolean;
  links: LLMClientArchitectureLinks;
}

export default function GettingStarted({ tree, styled, links }: GettingStartedProps) {
  const needsGuardrail = !hasGuardrail(tree);
  const needsTools = !hasTools(tree);
  const needsStyles = !styled;
  if (!needsGuardrail && !needsTools && !needsStyles) return null;

  const beneathSpec = interpolateNodes(
    gettext(
      "Paste it at the start of a new line beneath %(spec)s. If the manifest already has the same key with an empty list, such as %(empty)s, replace that line.",
    ),
    { spec: code("spec:"), empty: code("guardrails: []") },
  );

  return (
    <section className="architecture-getting-started" aria-labelledby="architecture-getting-started-title">
      <div className="architecture-kicker fw-bold fs-7 mb-3">{gettext("Next steps")}</div>
      <h2 id="architecture-getting-started-title" className="fs-2 fw-bolder text-gray-900 mb-3">
        {gettext("Make this LLMClient your own")}
      </h2>
      <p className="fs-6 text-gray-700 mw-750px mb-8">
        {gettext(
          "Most LLMClients have Guardrails, tools and a look of their own. This one is missing some of them. Each takes a few lines of YAML: copy an example below into the manifest, and save it.",
        )}
      </p>
      <div className="d-flex flex-column gap-8">
        {needsGuardrail && (
          <Suggestion icon="shield-tick" title={gettext("Add your first Guardrail")}>
            <p className="fs-6 text-gray-700 mb-3">
              {gettext(
                "A Guardrail screens the text that passes between the user and the LLM. An input Guardrail checks each prompt before it is sent to the LLM, and an output Guardrail checks each response before the user sees it. When it finds what it looks for, such as an email address, a prompt injection or a leaked password, it blocks the message, redacts what it found, or logs it.",
              )}
            </p>
            <p className="fs-6 text-gray-700 mb-5">
              {gettext(
                "Guardrails are ordinary software, not the LLM's judgment, so they enforce your rules however the LLM behaves. Smarter comes with built-in Guardrails for the most common cases, which every LLMClient may use by name: personal data, secrets, prompt injection, moderation, off-topic prompts and more.",
              )}
            </p>
            <div className="row g-6 align-items-start">
              <div className="col-12 col-lg-6">
                <Steps manifestUrl={tree.url} where={beneathSpec} />
                <div className="d-flex flex-wrap align-items-center gap-4 fs-7">
                  <BrowseLink href={links.guardrailsUrl}>{gettext("Browse the Guardrails")}</BrowseLink>
                  <DocsLink href={DOCS_URLS.builtInGuardrails}>{gettext("Built-in Guardrails")}</DocsLink>
                  <DocsLink href={DOCS_URLS.guardrails}>{gettext("Guardrails")}</DocsLink>
                </div>
              </div>
              <div className="col-12 col-lg-6">
                <ManifestSnippet snippet={GUARDRAIL_SNIPPET} label={gettext("Two built-in Guardrails")} />
                <p className="fs-8 text-gray-500 mt-2 mb-0">
                  {interpolateNodes(
                    gettext(
                      "%(pii)s removes credit card numbers, email addresses and phone numbers from each prompt, and %(injection)s blocks prompts that try to override the LLMClient's instructions. Neither calls an LLM.",
                    ),
                    { pii: code("pii_redaction_input"), injection: code("prompt_injection_keyword_input") },
                  )}
                </p>
              </div>
            </div>
          </Suggestion>
        )}

        {needsTools && (
          <Suggestion icon="wrench" title={gettext("Add your first tool")}>
            <p className="fs-6 text-gray-700 mb-3">
              {gettext(
                "An LLM knows only what it was trained on and what is in its prompt. Tools give it everything else: today's weather, a row in your database, a calculation that it would otherwise guess at. Smarter offers the LLM the tools that the LLMClient lists, the LLM decides when to call one, and Smarter runs it and hands back the result.",
              )}
            </p>
            <p className="fs-6 text-gray-700 mb-5">
              {gettext(
                "There are three ways to add tools, which differ in who writes them and where they run. An LLMClient may use all three at once.",
              )}
            </p>
            <Steps manifestUrl={tree.url} where={beneathSpec} />
            <div className="row g-5 mb-5">
              <Tool
                title={gettext("Plugins")}
                description={gettext(
                  "A plugin is a manifest that configures one of Smarter's built-in tool patterns: answer from static data, run a SQL query, call a REST api, follow a skill, search the web, or search for images. Nothing is coded or installed, and it runs on Smarter.",
                )}
                choose={gettext("for your own data, databases and apis, without writing code.")}
                snippet={PLUGIN_SNIPPET}
                caption={gettext(
                  "A sample static plugin about a fictional candy, which needs no Connection or Secret. Then ask the LLMClient about the Everlasting Gobstopper.",
                )}
                browse={<BrowseLink href={links.pluginsUrl}>{gettext("Browse the plugins")}</BrowseLink>}
                docs={<DocsLink href={DOCS_URLS.plugins}>{gettext("Plugins")}</DocsLink>}
              />
              <Tool
                title={gettext("Extensions")}
                description={gettext(
                  "An Extension is Python code, packaged and published to the Smarter Extension registry, that a platform administrator installs, much as a WordPress administrator installs a plugin. Its tools do whatever Python can do, and they run on Smarter.",
                )}
                choose={gettext("when a tool needs real code, or for a ready-made tool that is already installed.")}
                snippet={EXTENSION_SNIPPET}
                caption={gettext(
                  "An official Extension, which does arithmetic exactly. The Extensions page lists those that are installed on this platform.",
                )}
                browse={<BrowseLink href={links.extensionsUrl}>{gettext("Browse the Extensions")}</BrowseLink>}
                docs={<DocsLink href={DOCS_URLS.extensions}>{gettext("Extensions")}</DocsLink>}
              />
              <Tool
                title={gettext("MCPClients")}
                description={gettext(
                  "An MCPClient is a manifest that connects to a remote MCP server: a third party's tools, published with the Model Context Protocol. Smarter offers the server's tools to the LLM and calls them on that server. Nothing is coded, and nothing runs on Smarter.",
                )}
                choose={gettext(
                  "for a service that already publishes an MCP server, such as GitHub, Notion or Stripe.",
                )}
                snippet={MCPCLIENT_SNIPPET}
                caption={gettext(
                  "An example MCPClient for DeepWiki, which documents public GitHub repositories, and requires no authentication.",
                )}
                browse={<BrowseLink href={links.mcpClientsUrl}>{gettext("Browse the MCPClients")}</BrowseLink>}
                docs={<DocsLink href={DOCS_URLS.mcpClients}>{gettext("MCPClients")}</DocsLink>}
              />
            </div>
            <div className="d-flex flex-wrap align-items-center gap-4 fs-7">
              <DocsLink href={DOCS_URLS.toolsCompared}>
                {gettext("Plugins, Extensions and MCP servers compared")}
              </DocsLink>
              <DocsLink href={DOCS_URLS.extensibility}>{gettext("Extensibility")}</DocsLink>
            </div>
          </Suggestion>
        )}

        {needsStyles && (
          <Suggestion icon="brush" title={gettext("Style its chat")}>
            <p className="fs-6 text-gray-700 mb-3">
              {gettext(
                "This LLMClient's chat has Smarter's default look. A few lines of styles give it yours: your logo in the header, your colors on the message bubbles, your font, a picture behind the conversation. They apply in the workbench and on every web page that embeds the chat. You don't need to know CSS, and every setting is optional.",
              )}
            </p>
            <div className="row g-6 align-items-start">
              <div className="col-12 col-lg-6">
                <Steps
                  manifestUrl={tree.url}
                  where={interpolateNodes(
                    gettext(
                      "Styles go in %(styles)s, beside %(prompt)s: paste it at the start of the line after the last line of %(prompt)s, with the same indent as %(prompt)s.",
                    ),
                    { styles: code("spec.config.styles"), prompt: code("prompt:") },
                  )}
                />
                <div className="d-flex flex-wrap align-items-center gap-4 fs-7">
                  <DocsLink href={DOCS_URLS.styles}>{gettext("Styling your LLMClient's chat")}</DocsLink>
                </div>
              </div>
              <div className="col-12 col-lg-6">
                <ManifestSnippet snippet={STYLES_SNIPPET} label={gettext("The chat's styles")} />
                <p className="fs-8 text-gray-500 mt-2 mb-0">
                  {gettext(
                    "Smarter's logo, the Inter font, a dark header, and the user's messages in orange. Swap in your own logo's url and colors.",
                  )}
                </p>
              </div>
            </div>
          </Suggestion>
        )}
      </div>
    </section>
  );
}

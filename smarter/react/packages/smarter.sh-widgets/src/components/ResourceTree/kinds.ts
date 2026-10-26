/**
 * How the tree presents each kind of SAM resource: its color, what it does for the LLMClient, in a few words, and
 * its page in the documentation. Kinds of the same family, e.g. the plugins, share them. Each kind's icon is the
 * backend's, in the tree's nodes: see sam_kind_icon() in smarter.apps.api.v1.manifests.enum.
 */
import { gettext } from "@smarter/common";

/** The documentation that the cards link to. */
export const DOCS = "https://docs.smarter.sh/en/latest";

/** A Bootstrap color of the web console's theme, for a kind's icon and the accent of its card. */
export type Tone = "primary" | "info" | "success" | "warning" | "danger" | "dark" | "secondary";

export interface KindInfo {
  tone: Tone;
  /** What the resource does for the LLMClient that uses it, in a few words. */
  role: string;
  /** The kind's page in the documentation. */
  docsUrl: string;
}

const RESOURCES = `${DOCS}/smarter-resources`;
/** The kinds of plugin, which share a presentation. */
export const PLUGIN_KINDS = [
  "Plugin",
  "StaticPlugin",
  "ApiPlugin",
  "SkillPlugin",
  "SqlPlugin",
  "WebsearchPlugin",
  "ImageSearchPlugin",
];

/**
 * The presentation of a kind of resource. A kind that the tree doesn't know, e.g. a new one, has a neutral color
 * and the documentation of the manifests.
 *
 * @param kind - The SAM kind, e.g. "SqlPlugin", or "Extension", which is not a SAM kind.
 */
export function kindInfo(kind: string): KindInfo {
  if (PLUGIN_KINDS.includes(kind)) {
    return {
      tone: "success",
      role: gettext("A tool that the LLM can call"),
      docsUrl: `${RESOURCES}/smarter-llmtool.html`,
    };
  }
  switch (kind) {
    case "LLMClient":
      return {
        tone: "primary",
        role: gettext("A chat with an LLM, its tools, and its rules"),
        docsUrl: `${RESOURCES}/smarter-llmclient.html`,
      };
    case "Provider":
      return {
        tone: "info",
        role: gettext("The LLM provider whose models it prompts"),
        docsUrl: `${RESOURCES}/smarter-provider.html`,
      };
    case "MCPClient":
      return {
        tone: "info",
        role: gettext("The tools of a remote MCP server"),
        docsUrl: `${RESOURCES}/smarter-mcpclient.html`,
      };
    case "Extension":
      return {
        tone: "success",
        role: gettext("Tools installed from an extension package"),
        docsUrl: `${DOCS}/smarter-framework/smarter-extensions.html`,
      };
    case "Guardrail":
      return {
        tone: "dark",
        role: gettext("Screens prompts and responses"),
        docsUrl: `${RESOURCES}/smarter-guardrail.html`,
      };
    case "ApiConnection":
      return {
        tone: "warning",
        role: gettext("How a plugin reaches a remote api"),
        docsUrl: `${RESOURCES}/smarter-connection.html`,
      };
    case "SqlConnection":
      return {
        tone: "warning",
        role: gettext("How a plugin reaches a database"),
        docsUrl: `${RESOURCES}/smarter-connection.html`,
      };
    case "Secret":
      return {
        tone: "danger",
        role: gettext("An encrypted credential"),
        docsUrl: `${RESOURCES}/smarter-secret.html`,
      };
    case "SmarterAuthToken":
      return {
        tone: "warning",
        role: gettext("The api key that its url requires"),
        docsUrl: `${RESOURCES}/smarter-authtoken.html`,
      };
    case "CustomDomain":
      return {
        tone: "info",
        role: gettext("The domain that it is served from"),
        docsUrl: `${RESOURCES}/smarter-custom-domain.html`,
      };
    case "LLMHost":
    case "LLMHostCompute":
      return {
        tone: "secondary",
        role: gettext("Compute that hosts an LLM"),
        docsUrl: `${RESOURCES}/smarter-llmhost.html`,
      };
    case "Orchestrator":
      return {
        tone: "primary",
        role: gettext("Coordinates several LLMClients"),
        docsUrl: `${RESOURCES}/smarter-orchestrator.html`,
      };
    case "Proxy":
      return {
        tone: "secondary",
        role: gettext("Forwards requests to an LLM provider"),
        docsUrl: `${RESOURCES}/smarter-proxy.html`,
      };
    case "Vectorstore":
      return {
        tone: "info",
        role: gettext("Documents, indexed for search"),
        docsUrl: `${RESOURCES}/smarter-vectorstore.html`,
      };
    case "Vectorsearch":
      return {
        tone: "info",
        role: gettext("Searches a vector store"),
        docsUrl: `${RESOURCES}/smarter-vectorsearch.html`,
      };
    case "Budget":
      return {
        tone: "secondary",
        role: gettext("Limits what it may spend"),
        docsUrl: `${RESOURCES}/smarter-budget.html`,
      };
    default:
      return {
        tone: "secondary",
        role: gettext("A SAM resource"),
        docsUrl: `${DOCS}/smarter-framework/smarter-manifests.html`,
      };
  }
}

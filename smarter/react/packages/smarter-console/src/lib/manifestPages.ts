/**
 * The manifest pages that have moved into the console: each resource's page, where its manifest can be edited, at
 * the path that Django served it at. A page's id is the resource's hashed id, or an api key's key id; with the
 * prefix of its model's record locators, it makes the resource's record locator, e.g. guardrail-rMTAwx, by which
 * the resource api, /api/web/dashboard/resource/<record locator>/, finds it and its kind. See
 * smarter.lib.manifest.record_locator.console_paths, which builds the same paths.
 */
import type { ConsoleSession } from "@/contract.gen";
import { DASHBOARD_API } from "@/lib/dashboard";

export interface ManifestPage {
  /** The console's route, e.g. /guardrail/guardrails/:id. */
  path: string;
  /** The prefix of the record locators of the page's model, e.g. guardrail. */
  prefix: string;
  /** The list to go back to after the resource is deleted. */
  listPath: string;
  /** Whether the session may see the page, as for its list: see lib/lists. */
  visible?: (session: ConsoleSession) => boolean;
}

export const MANIFEST_PAGES: ManifestPage[] = [
  { path: "/authtoken/:id", prefix: "smarterauthtoken", listPath: "/authtoken" },
  { path: "/budget/budgets/:id", prefix: "budget", listPath: "/budget" },
  { path: "/connection/connections/api-connection/:id", prefix: "apiconnection", listPath: "/connection" },
  { path: "/connection/connections/sql-connection/:id", prefix: "sqlconnection", listPath: "/connection" },
  { path: "/guardrail/guardrails/:id", prefix: "guardrail", listPath: "/guardrail" },
  { path: "/llm-tools/plugins/:id", prefix: "pluginmeta", listPath: "/llm-tools" },
  { path: "/llmclient/custom-domains/:id", prefix: "llmclientcustomdomain", listPath: "/llmclient/custom-domains" },
  { path: "/llmhost/compute/:id", prefix: "llmhostcompute", listPath: "/llmhost/compute" },
  { path: "/llmhost/llmhosts/:id", prefix: "llmhost", listPath: "/llmhost" },
  { path: "/mcpclient/mcpclients/:id", prefix: "mcpclient", listPath: "/mcpclient" },
  { path: "/orchestrator/orchestrators/:id", prefix: "orchestrator", listPath: "/orchestrator" },
  { path: "/provider/providers/:id", prefix: "provider", listPath: "/provider" },
  {
    path: "/proxy/proxies/:id",
    prefix: "proxy",
    listPath: "/proxy",
    visible: (session) => session.flags.proxy,
  },
  { path: "/secret/secrets/:id", prefix: "secret", listPath: "/secret" },
  { path: "/vectorsearch/vectorsearchs/:id", prefix: "vectorsearch", listPath: "/vectorsearch" },
  {
    path: "/vectorstore/vectors/:id",
    prefix: "vectorstoremeta",
    listPath: "/vectorstore",
    visible: (session) => session.flags.vectorstore,
  },
];

/** The record locator of a page's resource. */
export function recordLocator(page: ManifestPage, id: string): string {
  return `${page.prefix}-${id}`;
}

/** The url of a resource's detail in the resource api, by its record locator alone. */
export function resourceUrl(locator: string): string {
  return `${DASHBOARD_API}/resource/${encodeURIComponent(locator)}/`;
}

/** The cli api, with which the manifest editor validates, saves, clones and deletes the manifest. */
export const CLI_API = "/api/v1/cli";
export const KIND_PLACEHOLDER = "__kind__";
export const manifestEditorUrls = {
  apply: `${CLI_API}/apply/`,
  validate: `${CLI_API}/validate/`,
  delete: `${CLI_API}/delete/${KIND_PLACEHOLDER}/`,
};

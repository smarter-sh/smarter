/**
 * The LLMClient architecture's contract: generated from contract/llmclient-architecture.schema.json by
 * scripts/contract-types.mjs. Do not edit; run `npm run contract:types`.
 */

/**
 * The tree of the SAM resources that an LLMClient is built from, which the Prompt Engineer's Workbench draws in its Architecture tab. Generated from smarter.apps.prompt.views.detailviews.architecture_contract; do not edit.
 */
export interface SmarterLLMClientArchitectureContract {
  [k: string]: unknown;
}
/**
 * A resource in a dependency tree: the resource, and, recursively, every resource that it uses.
 *
 * It is the opposite direction of :class:`SAMDependency`, which lists the resources that depend
 * on a resource. An LLMClient's tree has its Provider, its plugins, their Connections, and those
 * Connections' Secrets. See :meth:`smarter.lib.manifest.broker.AbstractBroker.dependency_tree`.
 *
 * A resource that the user may not read keeps its kind and record locator, so that the tree still
 * shows that something is there, but not its name, owner or url, or what it uses in turn.
 *
 * Example:
 *
 * .. code-block:: json
 *
 *     {
 *       "kind": "LLMClient",
 *       "icon": "artificial-intelligence",
 *       "name": "stackademy_sql",
 *       "owner": "Ada Lovelace (ada)",
 *       "recordLocator": "llmclient-rMTAwMDAxMwx",
 *       "url": "/workbench/llm-clients/rMTAwMDAxMwx/manifest/",
 *       "readable": true,
 *       "children": [
 *         {
 *           "kind": "SqlPlugin",
 *           "icon": "file-sheet",
 *           "name": "stackademy_sql",
 *           "owner": "Ada Lovelace (ada)",
 *           "recordLocator": "pluginmeta-rMTEx",
 *           "url": "/llm-tools/plugins/rMTEx/",
 *           "readable": true,
 *           "children": []
 *         }
 *       ]
 *     }
 *
 * This interface was referenced by `SmarterLLMClientArchitectureContract`'s JSON-Schema
 * via the `definition` "SAMDependencyTreeNode".
 */
export interface SAMDependencyTreeNode {
  /**
   * children[List]: The resources that this resource uses, each with its own tree. Read only.
   */
  children: SAMDependencyTreeNode[];
  /**
   * icon[String]: The kind's icon in the web console, a Keen Icons name without its ki- prefix, e.g. lock-2 for a Secret. See SAMKinds.icon(). Read only.
   */
  icon: string;
  /**
   * kind[String]: The SAM kind of the resource, e.g. LLMClient. Read only.
   */
  kind: string;
  /**
   * name[String]: The name of the resource. None if the user may not read it. Read only.
   */
  name: string | null;
  /**
   * owner[String]: Who owns the resource: its owner's full name and username, e.g. Ada Lovelace (ada), or an Extension's publisher. None if the user may not read it, or if it has no owner. Read only.
   */
  owner: string | null;
  /**
   * readable[Boolean]: Whether the user may read the resource. Read only.
   */
  readable: boolean;
  /**
   * recordLocator[String]: The resource's record locator, e.g. llmclient-rMTAwMDAxMwx, from which its web console url is derived. None for a resource that has none, e.g. a User. Read only.
   */
  recordLocator: string | null;
  /**
   * url[String]: The path of the resource's manifest page in the web console, where its manifest can be edited, derived from its record locator. None if it has no page, or if the user may not read it. Read only.
   */
  url: string | null;
  [k: string]: unknown;
}

/**
 * A resource in an LLMClient's tree: the resource, and, recursively, every resource that it uses. It is the shape of
 * the backend's smarter.lib.manifest.models.SAMDependencyTreeNode, from which @smarter/llmclient-architecture
 * generates its SAMDependencyTreeNode type, so that a tree of that type is a ResourceTreeNode too.
 */
export interface ResourceTreeNode {
  /** The SAM kind of the resource, e.g. LLMClient, or Extension. */
  kind: string;
  /** The kind's icon, a Keen Icons name without its ki- prefix, e.g. lock-2. */
  icon: string;
  /** The resource's name, or null if the user may not read it. */
  name: string | null;
  /** Who owns it, e.g. Ada Lovelace (ada), or null. A public page leaves owners out. */
  owner: string | null;
  /** Its record locator, e.g. llmclient-rMTAwMDAxMwx, or null for a resource that has none. */
  recordLocator: string | null;
  /** Its page in the web console, where its manifest can be edited, or null. A public page leaves urls out. */
  url: string | null;
  /** Whether the user may read it. A resource that they may not read shows its kind and record locator only. */
  readable: boolean;
  /** The resources that it uses. */
  children: ResourceTreeNode[];
}

/**
 * A resource's detail, from the url of a list row's detailUrl: its manifest, the resources that it uses, and those
 * that use it. It is the JSON of the backend's smarter.apps.dashboard.resource_detail.ResourceDetail.
 */
import fetchDjangoUrl from "../../lib/django";
import type { SessionContext } from "../../lib/Types";
import type { ResourceTreeNode } from "../ResourceTree/types";

export interface ResourceDetailData {
  /** The resource's SAM kind, e.g. Guardrail. */
  kind: string;
  name: string | null;
  /** Its record locator, e.g. guardrail-rMTAwx. */
  recordLocator: string;
  /** Its manifest page in the web console, where its manifest can be edited, or null. */
  url: string | null;
  /** Its manifest, as YAML, or null if it could not be read. */
  manifest: string | null;
  /** Why the manifest could not be read, or "". */
  manifestError: string;
  /** The resource, and every resource that it uses, recursively. */
  tree: ResourceTreeNode;
  /** The resources that use it, without their own children. */
  dependents: ResourceTreeNode[];
}

/** Fetch a resource's detail, or throw an Error with the server's message. */
export async function fetchResourceDetail(sessionContext: SessionContext, url: string): Promise<ResourceDetailData> {
  const response = await fetchDjangoUrl(sessionContext, url, JSON.stringify({}));
  const body = (await response.json().catch(() => null)) as (ResourceDetailData & { error?: string }) | null;
  if (!response.ok || !body) {
    throw new Error(body?.error || `${response.status} ${response.statusText}`);
  }
  return body;
}

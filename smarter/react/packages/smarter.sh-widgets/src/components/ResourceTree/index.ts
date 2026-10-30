/**
 * ResourceTree widget: an LLMClient's architecture, the tree of the SAM resources that it is built from.
 *
 * The widget lives in @smarter/common, so that the web console's resource lists can show it too, in a resource's
 * detail. @smarter/common is not published to npm, and the library bundles it, so this module declares the
 * widget's public types itself, rather than re-exporting them: the library's type declarations must not refer to
 * @smarter/common. Each binding below is typed with them, so the build fails if the two ever disagree.
 */
import type { ComponentType } from "react";
import {
  branchIds as commonBranchIds,
  childId as commonChildId,
  countResources as commonCountResources,
  depth as commonDepth,
  kindInfo as commonKindInfo,
  PLUGIN_KINDS as COMMON_PLUGIN_KINDS,
  ResourceCard as CommonResourceCard,
  ResourceTree as CommonResourceTree,
  ROOT_ID as COMMON_ROOT_ID,
} from "@smarter/common";

/**
 * A resource in an LLMClient's tree: the resource, and, recursively, every resource that it uses. It is the shape of
 * the backend's smarter.lib.manifest.models.SAMDependencyTreeNode.
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

/** A node's id in the tree: the indexes of its ancestors and itself, e.g. "0.2.1", since a resource can appear twice. */
export type NodeId = string;

/** A Bootstrap color of the web console's theme, for a kind's icon and the accent of its card. */
export type Tone = "primary" | "info" | "success" | "warning" | "danger" | "dark" | "secondary";

/** How the tree presents a kind of resource. */
export interface KindInfo {
  tone: Tone;
  /** What the resource does for the LLMClient that uses it, in a few words. */
  role: string;
  /** The kind's page in the documentation. */
  docsUrl: string;
}

export interface ResourceTreeProps {
  tree: ResourceTreeNode;
  /** The ids of the resources whose children are hidden, for a controlled tree. */
  collapsed?: ReadonlySet<NodeId>;
  /** Hides or shows a resource's children, for a controlled tree. */
  onToggle?: (id: NodeId) => void;
  /** The tree's accessible name. */
  label?: string;
  /** For a tree that isn't controlled: whether it opens with every resource's children hidden, but the root's. */
  defaultCollapsed?: boolean;
}

export interface ResourceCardProps {
  node: ResourceTreeNode;
  /** The resource at the root of the tree, whose card stands out. */
  isRoot?: boolean;
}

export const ResourceTree: ComponentType<ResourceTreeProps> = CommonResourceTree;
export const ResourceCard: ComponentType<ResourceCardProps> = CommonResourceCard;
export const branchIds: (tree: ResourceTreeNode) => NodeId[] = commonBranchIds;
export const childId: (parent: NodeId, index: number) => NodeId = commonChildId;
export const countResources: (tree: ResourceTreeNode) => number = commonCountResources;
export const depth: (tree: ResourceTreeNode) => number = commonDepth;
export const kindInfo: (kind: string) => KindInfo = commonKindInfo;
export const PLUGIN_KINDS: readonly string[] = COMMON_PLUGIN_KINDS;
export const ROOT_ID: NodeId = COMMON_ROOT_ID;

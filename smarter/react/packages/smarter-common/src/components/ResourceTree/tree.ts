/** The tree's arithmetic: what the toolbar counts, and which nodes the Collapse all button closes. */
import type { ResourceTreeNode } from "./types";

/** A node's id in the tree: the indexes of its ancestors and itself, e.g. "0.2.1", since a resource can appear twice. */
export type NodeId = string;

/** The id of a node's child. */
export const childId = (parent: NodeId, index: number): NodeId => `${parent}.${index}`;

/** The root's id. */
export const ROOT_ID: NodeId = "0";

/** The number of resources in the tree, counting a resource that appears twice once. */
export function countResources(tree: ResourceTreeNode): number {
  const seen = new Set<string>();
  let anonymous = 0;
  const visit = (node: ResourceTreeNode) => {
    if (node.recordLocator) seen.add(node.recordLocator);
    else anonymous += 1;
    node.children.forEach(visit);
  };
  visit(tree);
  return seen.size + anonymous;
}

/** The number of levels below the root: 0 for an LLMClient that uses nothing. */
export function depth(tree: ResourceTreeNode): number {
  return tree.children.length ? 1 + Math.max(...tree.children.map(depth)) : 0;
}

/** The ids of the nodes that have children, except the root, which is always open. */
export function branchIds(tree: ResourceTreeNode): NodeId[] {
  const ids: NodeId[] = [];
  const visit = (node: ResourceTreeNode, id: NodeId) => {
    if (id !== ROOT_ID && node.children.length) ids.push(id);
    node.children.forEach((child, index) => visit(child, childId(id, index)));
  };
  visit(tree, ROOT_ID);
  return ids;
}

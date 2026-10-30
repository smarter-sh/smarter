/**
 * ResourceTree widget: an LLMClient's architecture, the tree of the SAM resources that it is built from. Each
 * resource is a card, and beneath it, joined by lines, are the cards of the resources that it uses. A resource that
 * uses others has a button that hides them, or shows them again. The web console's Architecture tab
 * (@smarter/llmclient-architecture) renders it with its toolbar, and smarter.sh beside each assistant's live chat.
 *
 * The tree is controlled, with collapsed and onToggle, or keeps which resources are collapsed itself.
 *
 * :param tree: The tree, as the web console's architecture view returns it.
 * :type tree: ResourceTreeNode
 * :param collapsed: The ids of the resources whose children are hidden, for a controlled tree.
 * :type collapsed: ReadonlySet<NodeId>
 * :param onToggle: Hides or shows a resource's children, for a controlled tree.
 * :type onToggle: (id: NodeId) => void
 * :param label: The tree's accessible name. Defaults to "The resources that this LLMClient is built from".
 * :type label: str
 * :param defaultCollapsed: For a tree that isn't controlled: whether it opens with every resource's children hidden,
 *     but the root's, so that it shows the LLMClient and the resources that it uses directly.
 * :type defaultCollapsed: bool
 *
 * :example:
 *
 *     <ResourceTree tree={tree} />
 *     <ResourceTree tree={tree} defaultCollapsed />
 */
import { useState } from "react";
import { gettext, interpolate, ngettext } from "../../lib/i18n";

import "./styles.css";
import ResourceCard from "./ResourceCard";
import { branchIds, childId, ROOT_ID, type NodeId } from "./tree";
import type { ResourceTreeNode } from "./types";

interface BranchProps {
  node: ResourceTreeNode;
  id: NodeId;
  collapsed: ReadonlySet<NodeId>;
  onToggle: (id: NodeId) => void;
}

function Branch({ node, id, collapsed, onToggle }: BranchProps) {
  const isRoot = id === ROOT_ID;
  const hasChildren = node.children.length > 0;
  const open = isRoot || !collapsed.has(id);
  const name = node.name ?? node.kind;
  const childrenId = `architecture-children-${id.replaceAll(".", "-")}`;
  return (
    <li className={`architecture-node${isRoot ? " architecture-node-root" : ""}`}>
      <div className="architecture-row">
        {!isRoot &&
          (hasChildren ? (
            <button
              type="button"
              className="architecture-toggle btn btn-icon btn-sm btn-light"
              aria-expanded={open}
              aria-controls={childrenId}
              title={
                open
                  ? interpolate(gettext("Hide what %(name)s uses"), { name })
                  : interpolate(gettext("Show what %(name)s uses"), { name })
              }
              onClick={() => onToggle(id)}
            >
              <i className={`ki-outline ki-${open ? "minus-square" : "plus-square"} fs-4`} aria-hidden="true" />
              <span className="visually-hidden">
                {open
                  ? interpolate(gettext("Hide what %(name)s uses"), { name })
                  : interpolate(gettext("Show what %(name)s uses"), { name })}
              </span>
            </button>
          ) : (
            <span className="architecture-toggle-spacer" aria-hidden="true" />
          ))}
        <ResourceCard node={node} isRoot={isRoot} />
        {hasChildren && !open && (
          <span className="architecture-hidden-count badge badge-light-secondary text-gray-700">
            {interpolate(ngettext("%(count)s more", "%(count)s more", node.children.length), {
              count: node.children.length,
            })}
          </span>
        )}
      </div>
      {hasChildren && open && (
        <ul className="architecture-children" id={childrenId}>
          {node.children.map((child, index) => (
            <Branch
              key={childId(id, index)}
              node={child}
              id={childId(id, index)}
              collapsed={collapsed}
              onToggle={onToggle}
            />
          ))}
        </ul>
      )}
    </li>
  );
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

export default function ResourceTree({
  tree,
  collapsed,
  onToggle,
  label,
  defaultCollapsed = false,
}: ResourceTreeProps) {
  const [ownCollapsed, setOwnCollapsed] = useState<ReadonlySet<NodeId>>(
    () => new Set(defaultCollapsed ? branchIds(tree) : []),
  );
  const toggleOwn = (id: NodeId) =>
    setOwnCollapsed((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  return (
    <ul className="architecture-tree" aria-label={label ?? gettext("The resources that this LLMClient is built from")}>
      <Branch node={tree} id={ROOT_ID} collapsed={collapsed ?? ownCollapsed} onToggle={onToggle ?? toggleOwn} />
    </ul>
  );
}

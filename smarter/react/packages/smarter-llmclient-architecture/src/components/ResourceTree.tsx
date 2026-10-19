/**
 * The tree of resources: each resource's card, and beneath it, joined by lines, the cards of the resources that it
 * uses. A resource that uses others has a button that hides them, or shows them again.
 */
import { gettext, interpolate, ngettext } from "@smarter/common";

import ResourceCard from "./ResourceCard";
import { childId, ROOT_ID, type NodeId } from "../lib/tree";
import type { SAMDependencyTreeNode } from "../lib/types";

interface BranchProps {
  node: SAMDependencyTreeNode;
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

interface ResourceTreeProps {
  tree: SAMDependencyTreeNode;
  /** The ids of the resources whose children are hidden. */
  collapsed: ReadonlySet<NodeId>;
  onToggle: (id: NodeId) => void;
}

export default function ResourceTree({ tree, collapsed, onToggle }: ResourceTreeProps) {
  return (
    <ul className="architecture-tree" aria-label={gettext("The resources that this LLMClient is built from")}>
      <Branch node={tree} id={ROOT_ID} collapsed={collapsed} onToggle={onToggle} />
    </ul>
  );
}

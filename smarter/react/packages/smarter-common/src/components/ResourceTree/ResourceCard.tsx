/**
 * One resource of the tree, as a card: its kind, its name and its owner. A resource that the user may not read is a
 * locked card, with its kind and record locator only.
 *
 * With onOpen, e.g. in a resource's detail dialog, the card shows the resource's own detail, where its manifest can
 * be read, and edited from there. Without it, e.g. in the Prompt Engineer's Workbench's Architecture tab, the card
 * opens the resource's manifest page, where its manifest can be edited, in a new tab.
 */
import { gettext, interpolate } from "../../lib/i18n";

import { kindInfo } from "./kinds";
import type { ResourceTreeNode } from "./types";

export interface ResourceCardProps {
  node: ResourceTreeNode;
  /** The LLMClient itself, at the root of the tree, whose card stands out. */
  isRoot?: boolean;
  /** Shows a resource's detail. A card that has it opens a readable resource that has a detailUrl. */
  onOpen?: (node: ResourceTreeNode) => void;
}

export default function ResourceCard({ node, isRoot = false, onOpen }: ResourceCardProps) {
  const info = kindInfo(node.kind);
  const locked = !node.readable;
  const showsDetail = !locked && !!onOpen && !!node.detailUrl;
  const opens = showsDetail || (!locked && !!node.url);
  const name = node.name ?? node.recordLocator ?? node.kind;
  const classes = [
    "architecture-card",
    `architecture-card-${info.tone}`,
    isRoot ? "architecture-card-root" : "",
    locked ? "architecture-card-locked" : "",
    opens ? "architecture-card-link" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <article className={classes} aria-label={`${node.kind} ${name}`}>
      <span className={`architecture-card-icon text-${info.tone} bg-light-${info.tone}`} aria-hidden="true">
        <i className={`ki-outline ki-${locked ? "lock-3" : node.icon}`} data-testid="architecture-card-icon" />
      </span>
      <div className="architecture-card-body">
        <div className="d-flex align-items-center gap-2">
          {/* the kind is a product term, e.g. SqlPlugin, which isn't translated. */}
          <span className={`architecture-card-kind text-${info.tone}`}>{node.kind}</span>
          <a
            href={info.docsUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="architecture-card-docs text-gray-500 text-hover-primary"
            title={interpolate(gettext("About %(kind)s, in the documentation"), { kind: node.kind })}
          >
            <i className="ki-outline ki-information-5 fs-7" aria-hidden="true" />
            <span className="visually-hidden">
              {interpolate(gettext("About %(kind)s, in the documentation"), { kind: node.kind })}
            </span>
          </a>
        </div>
        {locked ? (
          <>
            <div className="architecture-card-name text-gray-600">{gettext("You can't read this resource")}</div>
            <div className="architecture-card-meta">
              <code className="architecture-card-locator">{node.recordLocator}</code>
            </div>
          </>
        ) : (
          <>
            {showsDetail ? (
              <button
                type="button"
                className="architecture-card-name stretched-link"
                title={interpolate(gettext("Show the detail of %(name)s"), { name })}
                onClick={() => onOpen?.(node)}
              >
                {name}
              </button>
            ) : opens ? (
              <a
                href={node.url ?? undefined}
                target="_blank"
                rel="noopener noreferrer"
                className="architecture-card-name stretched-link"
                title={interpolate(gettext("Open the manifest of %(name)s in a new tab"), { name })}
              >
                {name}
              </a>
            ) : (
              <div className="architecture-card-name">{name}</div>
            )}
            <div className="architecture-card-meta" title={info.role}>
              <span className="text-truncate">{info.role}</span>
            </div>
            {node.owner && (
              <div className="architecture-card-meta">
                <i className="ki-outline ki-profile-circle fs-7 me-1" aria-hidden="true" />
                <span className="visually-hidden">{gettext("Owner")}: </span>
                <span className="text-truncate">{node.owner}</span>
              </div>
            )}
          </>
        )}
      </div>
      {opens && (
        <span className="architecture-card-open text-gray-400" aria-hidden="true">
          <i className={`ki-outline ki-${showsDetail ? "right" : "arrow-up-right"}`} />
        </span>
      )}
    </article>
  );
}

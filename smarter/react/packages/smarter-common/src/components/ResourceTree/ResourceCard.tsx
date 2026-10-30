/**
 * One resource of the tree, as a card: its kind, its name and its owner. The card opens the resource's manifest
 * page, where its manifest can be edited, in a new tab. A resource that the user may not read is a locked card,
 * with its kind and record locator only.
 */
import { gettext, interpolate } from "../../lib/i18n";

import { kindInfo } from "./kinds";
import type { ResourceTreeNode } from "./types";

interface ResourceCardProps {
  node: ResourceTreeNode;
  /** The LLMClient itself, at the root of the tree, whose card stands out. */
  isRoot?: boolean;
}

export default function ResourceCard({ node, isRoot = false }: ResourceCardProps) {
  const info = kindInfo(node.kind);
  const locked = !node.readable;
  const opens = !locked && !!node.url;
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
            {opens ? (
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
          <i className="ki-outline ki-arrow-up-right" />
        </span>
      )}
    </article>
  );
}

/**
 * The tabs of a resource's detail that show what the backend says about it: its manifest, the hierarchy of the
 * resources that it uses, and the resources that use it. See ./api.ts.
 */
import { useMemo, useState } from "react";

import { gettext, interpolate, ngettext } from "../../lib/i18n";
import ResourceTree from "../ResourceTree/Component";
import ResourceCard from "../ResourceTree/ResourceCard";
import { branchIds, countResources, depth, type NodeId } from "../ResourceTree/tree";
import type { ResourceTreeNode } from "../ResourceTree/types";
import type { ResourceDetailData } from "./api";
import { CodeBlock } from "./code";
import { highlightYaml } from "./yaml";

/** How long the Copy button says "Copied", in milliseconds. */
export const COPIED_MS = 2000;

/** A tab's empty state: an icon, a title and an explanation. */
function EmptyState({ icon, title, children }: { icon: string; title: string; children?: React.ReactNode }) {
  return (
    <div className="smarter-detail-empty-state">
      <span className="smarter-detail-empty-state-icon" aria-hidden="true">
        <i className={`ki-outline ki-${icon}`} />
      </span>
      <p className="fw-semibold text-gray-800 mb-1">{title}</p>
      {children && <p className="text-gray-600 mb-0">{children}</p>}
    </div>
  );
}

/** The safe file name of a downloaded manifest, e.g. guardrail-pii_redaction.yaml. */
export function manifestFileName(kind: string, name: string | null): string {
  const base = `${kind}-${name ?? "manifest"}`.toLowerCase().replace(/[^a-z0-9_.-]+/g, "-");
  return `${base}.yaml`;
}

/** The Manifest tab: the resource's manifest, highlighted, with Copy, Download and Edit. */
export function ManifestTab({ detail }: { detail: ResourceDetailData }) {
  const [copied, setCopied] = useState(false);
  const lines = useMemo(() => (detail.manifest ? highlightYaml(detail.manifest) : []), [detail.manifest]);

  if (!detail.manifest) {
    return (
      <EmptyState icon="file-deleted" title={gettext("The manifest could not be read.")}>
        {detail.manifestError}
      </EmptyState>
    );
  }
  const manifest = detail.manifest;

  const copy = () => {
    void navigator.clipboard?.writeText(manifest).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), COPIED_MS);
    });
  };
  const download = () => {
    const url = URL.createObjectURL(new Blob([manifest], { type: "application/yaml" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = manifestFileName(detail.kind, detail.name);
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="smarter-detail-manifest">
      <div className="smarter-detail-tab-toolbar">
        <p className="text-gray-600 mb-0 me-auto">
          {interpolate(gettext("The manifest that declares this %(kind)s, as smarter describe returns it."), {
            kind: detail.kind,
          })}
        </p>
        <button type="button" className="btn btn-sm btn-light" onClick={copy}>
          <i className={`ki-outline ki-${copied ? "check" : "copy"} fs-5`} aria-hidden="true" />
          {copied ? gettext("Copied") : gettext("Copy")}
        </button>
        <button type="button" className="btn btn-sm btn-light" onClick={download}>
          <i className="ki-outline ki-file-down fs-5" aria-hidden="true" />
          {gettext("Download")}
        </button>
        {detail.url && (
          <a href={detail.url} className="btn btn-sm btn-light-primary">
            <i className="ki-outline ki-pencil fs-5" aria-hidden="true" />
            {gettext("Edit manifest")}
          </a>
        )}
      </div>
      <CodeBlock lines={lines} label={gettext("Manifest YAML")} className="smarter-code-block-manifest" />
    </div>
  );
}

/** Shows another resource's detail, in place of this one's: see ResourceDetail. */
type OnOpen = (node: ResourceTreeNode) => void;

/** The Hierarchy tab: the tree of the resources that the resource uses, recursively. Their cards show their detail. */
export function HierarchyTab({ detail, onOpen }: { detail: ResourceDetailData; onOpen?: OnOpen }) {
  const { tree } = detail;
  const [collapsed, setCollapsed] = useState<ReadonlySet<NodeId>>(() => new Set());
  const branches = branchIds(tree);
  const used = countResources(tree) - 1;
  const levels = depth(tree);
  const name = detail.name ?? detail.kind;

  const toggle = (id: NodeId) =>
    setCollapsed((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  return (
    <div className="smarter-detail-hierarchy">
      <div className="smarter-detail-tab-toolbar">
        <p className="text-gray-600 mb-0 me-auto" role="status">
          {used === 0
            ? interpolate(gettext("%(name)s uses no other resources."), { name })
            : interpolate(
                ngettext(
                  "%(name)s uses %(count)s resource, %(levels)s levels deep.",
                  "%(name)s uses %(count)s resources, %(levels)s levels deep.",
                  used,
                ),
                { name, count: used, levels },
              )}
        </p>
        {branches.length > 0 && (
          <>
            <button
              type="button"
              className="btn btn-sm btn-light"
              disabled={collapsed.size === 0}
              onClick={() => setCollapsed(new Set())}
            >
              <i className="ki-outline ki-plus-square fs-5" aria-hidden="true" />
              {gettext("Expand all")}
            </button>
            <button
              type="button"
              className="btn btn-sm btn-light"
              disabled={collapsed.size === branches.length}
              onClick={() => setCollapsed(new Set(branches))}
            >
              <i className="ki-outline ki-minus-square fs-5" aria-hidden="true" />
              {gettext("Collapse all")}
            </button>
          </>
        )}
      </div>
      <div className="smarter-detail-tree">
        <ResourceTree
          tree={tree}
          collapsed={collapsed}
          onToggle={toggle}
          label={interpolate(gettext("The resources that %(name)s uses"), { name })}
          onOpen={onOpen}
        />
      </div>
    </div>
  );
}

/** The Dependencies tab: the resources that use this one, and that keep it from being deleted. Their cards show their
 * detail. */
export function DependenciesTab({ detail, onOpen }: { detail: ResourceDetailData; onOpen?: OnOpen }) {
  const name = detail.name ?? detail.kind;
  if (detail.dependents.length === 0) {
    return (
      <EmptyState icon="check-circle" title={interpolate(gettext("No other resource uses %(name)s."), { name })}>
        {gettext("Nothing depends on it, so deleting it breaks nothing.")}
      </EmptyState>
    );
  }
  return (
    <div className="smarter-detail-dependencies">
      <div className="smarter-detail-tab-toolbar">
        <p className="text-gray-600 mb-0">
          {interpolate(
            ngettext(
              "%(count)s resource uses %(name)s. It can't be deleted until that resource stops using it.",
              "%(count)s resources use %(name)s. It can't be deleted until they stop using it.",
              detail.dependents.length,
            ),
            { count: detail.dependents.length, name },
          )}
        </p>
      </div>
      <ul className="smarter-detail-dependents" aria-label={interpolate(gettext("What uses %(name)s"), { name })}>
        {detail.dependents.map((node, index) => (
          <li key={node.recordLocator ?? index}>
            <ResourceCard node={node} onOpen={onOpen} />
          </li>
        ))}
      </ul>
    </div>
  );
}

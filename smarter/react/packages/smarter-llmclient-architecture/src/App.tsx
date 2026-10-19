/**
 * An LLMClient's architecture: an introduction to SAM resources and their manifests, then the tree of the
 * resources that the LLMClient is built from, as cards that open each resource's manifest in a new tab, then the
 * next steps for an LLMClient that has no Guardrail, no tools or no styles. The Prompt Engineer's Workbench renders
 * it in its Console's "Architecture" tab.
 */
import { useState } from "react";
import { gettext, interpolate, ngettext } from "@smarter/common";

import GettingStarted from "./components/GettingStarted";
import Introduction from "./components/Introduction";
import ResourceTree from "./components/ResourceTree";
import { DOCS_URLS } from "./lib/const";
import { branchIds, countResources, depth, type NodeId } from "./lib/tree";
import type { LLMClientArchitecture } from "./lib/types";
import "./styles.css";

export interface ArchitectureProps {
  /** The LLMClient's architecture, from its architecture view: its tree, whether it is styled, and links. */
  architecture: LLMClientArchitecture;
  /** Fetches the tree again, e.g. after a manifest was changed in another tab. Without it, there is no Reload button. */
  onReload?: () => void;
}

export default function App({ architecture, onReload }: ArchitectureProps) {
  const { tree, styled, links } = architecture;
  const [collapsed, setCollapsed] = useState<ReadonlySet<NodeId>>(() => new Set());
  const branches = branchIds(tree);
  const resources = countResources(tree);
  const levels = depth(tree);

  const toggle = (id: NodeId) =>
    setCollapsed((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  return (
    <div className="smarter-architecture">
      <Introduction />
      <section className="architecture-canvas">
        <div className="architecture-toolbar d-flex flex-wrap align-items-center gap-3 mb-6">
          <div className="fs-7 text-gray-600 me-auto" role="status">
            {interpolate(ngettext("%(count)s resource", "%(count)s resources", resources), { count: resources })}
            {" · "}
            {interpolate(ngettext("%(count)s level deep", "%(count)s levels deep", levels), { count: levels })}
          </div>
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
          {onReload && (
            <button
              type="button"
              className="btn btn-sm btn-light-primary"
              onClick={onReload}
              title={gettext("Fetch the tree again, after a manifest was changed")}
            >
              <i className="ki-outline ki-arrows-circle fs-5" aria-hidden="true" />
              {gettext("Reload")}
            </button>
          )}
        </div>
        <ResourceTree tree={tree} collapsed={collapsed} onToggle={toggle} />
        <p className="architecture-footnote fs-8 text-gray-500 mt-8 mb-0">
          <i className="ki-outline ki-lock-3 fs-7 me-1" aria-hidden="true" />
          {gettext("A locked card is a resource that you can't read, such as another account's.")}{" "}
          <a href={DOCS_URLS.ownership} target="_blank" rel="noopener noreferrer">
            {gettext("Who owns a resource, and who may read it")}
          </a>
        </p>
      </section>
      <GettingStarted tree={tree} styled={styled} links={links} />
    </div>
  );
}

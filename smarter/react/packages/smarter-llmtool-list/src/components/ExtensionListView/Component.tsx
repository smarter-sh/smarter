/**
 * ExtensionListView
 *
 * Renders a responsive, table-based, read-only list of the installed Extensions that the user's
 * account may use, for the Extensions tab.
 * Features:
 * - Displays Extension information in the same styled table as the LLMTool list, with columns for
 *   name, slug, version, publisher, description, dates and status.
 * - Is read-only for every user: it has no Toolbar, because superusers manage extensions in the
 *   Extensions console.
 * - Formats dates and status using shared utilities.
 * - Shows skeleton (ghost) rows while loading, and supports incremental rendering for large lists.
 *
 * Props:
 * @param isLoading - Whether the Extension data is loading (shows skeleton rows if true).
 * @param ghostRows - Number of skeleton rows to display while loading.
 * @param objects - Array of Extension objects to display.
 * @param sorting - The sort of the list, which its sortable column headers change.
 *
 * Usage:
 * <ExtensionListView
 *   sessionContext={sessionContext}
 *   objects={extensions}
 *   isLoading={isLoading}
 *   ghostRows={ghostRows}
 *   onRequery={onRequery}
 * />
 */
import React, { useState, useEffect } from "react";

import { formatDateTime, Loading, SortableHeader } from "@smarter/common";
import type { Sorting } from "@smarter/common";

import type { Extension, ExtensionListViewProps } from "@/lib/Types";
import { ExtensionStatusBar } from "@/components/ExtensionStatusBar";
import { loggerPrefix } from "@/lib/const";

import "@/components/ListView/styles.css";

/**
 * LoadingText
 *
 * Displays a muted "Loading..." text, used in skeleton or ghost rows to indicate loading state.
 */
const LoadingText = () => {
  return <span className="text-muted fw-semibold">Loading...</span>;
};

/**
 * TableHeader
 *
 * Renders the table header row for the Extension list. Its sortable columns sort the list, with
 * the list api (see SortableHeader).
 */
const TableHeader = ({ sorting }: { sorting?: Sorting }) => {
  return (
    <thead className="table-light border-bottom-2">
      <tr className="">
        <SortableHeader column="displayName" sorting={sorting} className=" p-1">
          Name
        </SortableHeader>
        <th className="">Slug</th>
        <SortableHeader column="version" sorting={sorting} className="">
          Version
        </SortableHeader>
        <SortableHeader column="publisher" sorting={sorting} className="d-none d-lg-table-cell">
          Publisher
        </SortableHeader>
        <SortableHeader column="description" sorting={sorting} className="">
          Description
        </SortableHeader>
        <SortableHeader column="updatedAt" sorting={sorting} className="d-none d-lg-table-cell width-100">
          Updated
        </SortableHeader>
        <th className="d-none d-md-table-cell">Status</th>
      </tr>
    </thead>
  );
};

/**
 * ExtensionName
 *
 * The extension's name, linked to its homepage when it has one.
 */
const ExtensionName = ({ extension }: { extension: Extension }) => {
  if (!extension.homepage) return <span>{extension.displayName}</span>;
  return (
    <a href={extension.homepage} target="_blank" rel="noopener noreferrer">
      {extension.displayName}
    </a>
  );
};

/**
 * ExtensionRow
 *
 * Renders a single Extension as a table row.
 *
 * @param extension - The Extension object to display.
 */
const ExtensionRow = React.memo(function ExtensionRow({ extension }: { extension: Extension }) {
  return (
    <tr className="" key={extension.id}>
      {/* Name */}
      <td className="p-1 m-0">
        <ExtensionName extension={extension} />
      </td>
      {/* Slug */}
      <td className="">
        <code>{extension.slug}</code>
      </td>
      {/* Version */}
      <td className="">{extension.version}</td>
      {/* Publisher */}
      <td className="d-none d-lg-table-cell">{extension.publisher}</td>
      {/* Description */}
      <td className="">{extension.description}</td>
      {/* Updated Date */}
      <td className="d-none d-lg-table-cell width-100">
        <span>{formatDateTime(extension.updatedAt, "relative", extension.createdAt)}</span>
      </td>
      {/* Status */}
      <td className="d-none d-md-table-cell ">
        <ExtensionStatusBar extension={extension} />
      </td>
    </tr>
  );
});

/**
 * ExtensionRowGhost
 *
 * A skeleton row component to display while Extension data is loading.
 */
const ExtensionRowGhost = React.memo(function ExtensionRowGhost() {
  return (
    <tr className="ghost">
      {/* Name */}
      <td className="p-1 m-0">
        <Loading />
      </td>
      {/* Slug */}
      <td className="">
        <LoadingText />
      </td>
      {/* Version */}
      <td className=""></td>
      {/* Publisher */}
      <td className="d-none d-lg-table-cell"></td>
      {/* Description */}
      <td className=""></td>
      {/* Updated Date */}
      <td className="d-none d-lg-table-cell width-100"></td>
      {/* Status */}
      <td className="d-none d-md-table-cell "></td>
    </tr>
  );
});

/**
 * ChunkedRows
 *
 * Incrementally renders Extension rows in chunks to avoid UI blocking.
 * Uses requestIdleCallback (if available) or setTimeout as a fallback to schedule rendering.
 *
 * @param extensions - Array of Extension objects to render.
 * @param chunkSize - Number of rows to render per chunk (default: 5).
 */
function ChunkedRows({ extensions, chunkSize = 5 }: { extensions: Extension[]; chunkSize?: number }) {
  const [visibleCount, setVisibleCount] = useState(chunkSize);

  useEffect(() => {
    if (visibleCount >= extensions.length) return;
    const next = () => setVisibleCount((c) => Math.min(c + chunkSize, extensions.length));
    if (window.requestIdleCallback) {
      const idleId = window.requestIdleCallback(next);
      return () => window.cancelIdleCallback(idleId);
    }
    const timeoutId = setTimeout(next, 0);
    return () => clearTimeout(timeoutId);
  }, [visibleCount, extensions.length, chunkSize]);
  return (
    <>
      {extensions.slice(0, visibleCount).map((extension) => (
        <ExtensionRow key={extension.id} extension={extension} />
      ))}
    </>
  );
}

/**
 * ExtensionListView
 *
 * Main component for displaying the read-only, table-based list of Extensions.
 * Handles loading state with skeleton rows and incremental rendering for large lists.
 */
export function ExtensionListView({ isLoading, ghostRows, objects, sorting }: ExtensionListViewProps) {
  console.debug(
    `${loggerPrefix} ExtensionListView() Rendering - {isLoading: ${isLoading}, ghostRows: ${ghostRows}, objects length: ${Array.isArray(objects) ? objects.length : "N/A"}}`,
  );
  return (
    <div className="table-responsive llmtool-list-table-wrap ps-3 pe-3">
      <table className="table table-striped table-hover align-middle border">
        <TableHeader sorting={sorting} />
        <tbody>
          {isLoading ? (
            Array.from({ length: ghostRows }).map((_, idx) => <ExtensionRowGhost key={idx} />)
          ) : (
            <ChunkedRows extensions={objects} />
          )}
        </tbody>
      </table>
    </div>
  );
}

export default ExtensionListView;

/**
 * ListView
 *
 * Renders a responsive, table-based list of LLMTool resources with key details and actions.
 * Features:
 * - Displays LLMTool information in a styled table with columns for name, dates, provider, model, status, and actions.
 * - Integrates Toolbar for per-llmtool actions (open, edit, clone, rename, delete).
 * - Formats dates and status using shared utilities.
 * - Shows skeleton (ghost) rows while loading, and supports incremental rendering for large lists.
 *
 * Props:
 * @param isLoading - Whether the LLMTool data is loading (shows skeleton rows if true).
 * @param ghostRows - Number of skeleton rows to display while loading.
 * @param sessionContext - Authentication and API context for actions.
 * @param llmtools - Array of LLMTool objects to display.
 * @param onRequery - Callback to refresh LLMTool data.
 *
 * Usage:
 * <ListView
 *   sessionContext={sessionContext}
 *   llmtools={llmtools}
 *   isLoading={isLoading}
 *   ghostRows={ghostRows}
 *   onRequery={onRequery}
 * />
 *
 * Intended for views where LLMTools are presented in a list/table format.
 */
import React, { useState, useEffect } from "react";

import { formatDateTime, gettext, Loading, SortableHeader } from "@smarter/common";
import type { SessionContext, Sorting } from "@smarter/common";

import type { LLMTool, LLMToolListViewProps } from "@/lib/Types";
import { Toolbar } from "@/components/Toolbar";
import { StatusBar } from "@/components/StatusBar";
import { loggerPrefix } from "@/lib/const";

import "@/components/ListView/styles.css";

/**
 * LoadingText
 *
 * Displays a muted "Loading..." text, typically used in skeleton or ghost rows to indicate loading state.
 */
const LoadingText = () => {
  return <span className="text-muted fw-semibold">{gettext("Loading...")}</span>;
};

/**
 * TableHeader
 *
 * Renders the table header row for the LLMTool list, including column titles for all displayed fields.
 * Its sortable columns sort the list, with the list api (see SortableHeader).
 */
const TableHeader = ({ sorting }: { sorting?: Sorting }) => {
  return (
    <thead className="table-light border-bottom-2">
      <tr className="">
        <SortableHeader column="name" sorting={sorting} className=" p-1">
          {gettext("Name")}
        </SortableHeader>
        <SortableHeader column="createdAt" sorting={sorting} className="d-none d-lg-table-cell width-100">
          {gettext("Created")}
        </SortableHeader>
        <SortableHeader column="updatedAt" sorting={sorting} className="d-none d-lg-table-cell width-100">
          {gettext("Updated")}
        </SortableHeader>
        <SortableHeader column="kind" sorting={sorting} className="">
          {gettext("Kind")}
        </SortableHeader>
        <SortableHeader column="description" sorting={sorting} className="">
          {gettext("Description")}
        </SortableHeader>
        <SortableHeader column="selector" sorting={sorting} className="min-width-150">
          {gettext("Selector")}
        </SortableHeader>
        <th className="d-none d-md-table-cell">{gettext("Status")}</th>
        <th className="">{gettext("Operations")}</th>
      </tr>
    </thead>
  );
};

/**
 * CreatedDate and UpdatedDate
 *
 * Format a row's creation date, and its last update relative to its creation.
 */
const CreatedDate = ({ date }: { date: string }) => {
  return <span>{formatDateTime(date, "date")}</span>;
};

const UpdatedDate = ({ date, createdAt }: { date: string; createdAt: string }) => {
  return <span>{formatDateTime(date, "relative", createdAt)}</span>;
};

/**
 * LLMToolRow
 *
 * Renders a single LLMTool as a table row, displaying its details and action toolbar.
 *
 * @param LLMTool - The LLMTool object to display.
 * @param sessionContext - Session context for actions.
 * @param onRequery - Callback to refresh LLMTool data after an action.
 */
const LLMToolRow = React.memo(function LLMToolRow({
  llmtool,
  sessionContext,
  onRequery,
}: {
  llmtool: LLMTool;
  sessionContext: SessionContext;
  onRequery: () => void;
}) {
  return (
    <tr className="" key={llmtool.id}>
      {/* Name */}
      <td className="p-1 m-0">
        {/* the row opens the plugin's detail: see TabbedListView. */}
        <span className="fw-semibold text-gray-900">{llmtool.name}</span>
      </td>
      {/* Created Date */}
      <td className="d-none d-lg-table-cell width-100">
        <CreatedDate date={llmtool.createdAt} />
      </td>
      {/* Updated Date */}
      <td className="d-none d-lg-table-cell width-100">
        <UpdatedDate date={llmtool.updatedAt} createdAt={llmtool.createdAt} />
      </td>
      {/* Kind */}
      <td className="">{llmtool.kind}</td>
      {/* Description */}
      <td className="">{llmtool.description}</td>
      {/* Selector */}
      <td className="min-width-150">{llmtool.selector.directive}</td>
      {/* Status */}
      <td className="d-none d-md-table-cell ">
        <StatusBar llmtool={llmtool} />
      </td>
      {/* Actions */}
      <td className="text-end ">
        <Toolbar sessionContext={sessionContext} llmtool={llmtool} onRequery={onRequery} />
      </td>
    </tr>
  );
});

/**
 * LLMToolRowGhost
 *
 * A skeleton row component to display while LLMTool data is loading.
 * It mimics the structure of a regular LLMToolRow but with placeholder content.
 */
const LLMToolRowGhost = React.memo(function LLMToolRowGhost() {
  console.debug(`${loggerPrefix} Rendering LLMToolRowGhost`);
  return (
    <tr className="ghost">
      {/* Name */}
      <td className="p-1 m-0">
        <Loading />
      </td>
      {/* Created Date */}
      <td className="d-none d-lg-table-cell width-100">
        <LoadingText />
      </td>
      {/* Updated Date */}
      <td className="d-none d-lg-table-cell width-100"></td>
      {/* Kind */}
      <td className=""></td>
      {/* Description */}
      <td className="min-width-150"></td>
      {/* Selector */}
      <td className="d-none d-xl-table-cell"></td>
      {/* Status */}
      <td className="d-none d-md-table-cell "></td>
      {/* Actions */}
      <td className="text-end "></td>
    </tr>
  );
});

/**
 * LLMToolRowGhosts
 *
 * Renders a specified number of skeleton (ghost) rows to indicate loading state in the LLMTool list.
 *
 * @param count - Number of skeleton rows to render.
 */
const LLMToolRowGhosts = React.memo(function LLMToolRowGhosts({ count }: { count: number }) {
  console.debug(`${loggerPrefix} Rendering LLMToolRowGhosts with count: ${count}`);
  return (
    <>
      {Array.from({ length: count }).map((_, idx) => (
        <LLMToolRowGhost key={idx} />
      ))}
    </>
  );
});

/**
 * ChunkedRows
 *
 * Incrementally renders LLMTool rows in chunks to avoid UI blocking.
 * Uses requestIdleCallback (if available) or setTimeout as a fallback to schedule rendering.
 *
 * @param llmtools - Array of LLMTool objects to render.
 * @param sessionContext - Session context for actions.
 * @param onRequery - Callback to refresh LLMTool data.
 * @param chunkSize - Number of rows to render per chunk (default: 5).
 */
function ChunkedRows({
  llmtools,
  sessionContext,
  onRequery,
  chunkSize = 5,
}: {
  llmtools: LLMTool[];
  sessionContext: SessionContext;
  onRequery: () => void;
  chunkSize?: number;
}) {
  const [visibleCount, setVisibleCount] = useState(chunkSize);

  useEffect(() => {
    if (visibleCount >= llmtools.length) return;
    const next = () => setVisibleCount((c) => Math.min(c + chunkSize, llmtools.length));
    if (window.requestIdleCallback) {
      const idleId = window.requestIdleCallback(next);
      return () => window.cancelIdleCallback(idleId);
    }
    const timeoutId = setTimeout(next, 0);
    return () => clearTimeout(timeoutId);
  }, [visibleCount, llmtools.length, chunkSize]);
  return (
    <>
      {llmtools.slice(0, visibleCount).map((llmtool) => (
        <LLMToolRow key={llmtool.id} llmtool={llmtool} sessionContext={sessionContext} onRequery={onRequery} />
      ))}
    </>
  );
}

/**
 * ListView
 *
 * Main component for displaying a responsive, table-based list of LLMTool resources.
 * Handles loading state with skeleton rows and incremental rendering for large lists.
 *
 * @param isLoading - Whether the LLMTool data is loading (shows skeleton rows if true).
 * @param ghostRows - Number of skeleton rows to display while loading.
 * @param sessionContext - Authentication and API context for actions.
 * @param llmtools - Array of LLMTool objects to display.
 * @param onRequery - Callback to refresh LLMTool data.
 * @param sorting - The sort of the list, which its sortable column headers change.
 */
export function ListView({ isLoading, ghostRows, sessionContext, objects, onRequery, sorting }: LLMToolListViewProps) {
  console.debug(
    `${loggerPrefix} ListView() Rendering ListView - {isLoading: ${isLoading}, ghostRows: ${ghostRows}, objects length: ${Array.isArray(objects) ? objects.length : "N/A"}}`,
  );
  return (
    <div className="table-responsive llmtool-list-table-wrap ps-3 pe-3">
      <table className="table table-striped table-hover align-middle border">
        <TableHeader sorting={sorting} />
        <tbody>
          {isLoading ? (
            <LLMToolRowGhosts count={ghostRows} />
          ) : (
            <ChunkedRows llmtools={objects} sessionContext={sessionContext} onRequery={onRequery} />
          )}
        </tbody>
      </table>
    </div>
  );
}

export default ListView;

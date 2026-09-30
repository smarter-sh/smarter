/**
 * ListView
 *
 * Renders a responsive, table-based list of vectorsearch resources with key details and actions.
 * Features:
 * - Displays vectorsearch information in a styled table with columns for name, dates, vectorsearch, model, vectorsearchs, status, and actions.
 * - Integrates Toolbar for per-vectorsearch actions (open, edit, clone, rename, delete).
 * - Formats dates and status using shared utilities.
 * - Shows skeleton (ghost) rows while loading, and supports incremental rendering for large lists.
 *
 * Props:
 * @param isLoading - Whether the vectorsearch data is loading (shows skeleton rows if true).
 * @param ghostRows - Number of skeleton rows to display while loading.
 * @param sessionContext - Authentication and API context for actions.
 * @param vectorsearchs - Array of vectorsearch objects to display.
 * @param onRequery - Callback to refresh vectorsearch data.
 *
 * Usage:
 * <ListView
 *   sessionContext={sessionContext}
 *   vectorsearchs={vectorsearchs}
 *   isLoading={isLoading}
 *   ghostRows={ghostRows}
 *   onRequery={onRequery}
 * />
 *
 * Intended for views where vectorsearchs are presented in a list/table format.
 */
import React, { useState, useEffect } from "react";

import { Loading, formatDateTime } from "@smarter/common";
import type { SessionContext } from "@smarter/common";

import type { Vectorsearch, VectorsearchListViewProps } from "@/lib/Types";
import { Toolbar } from "@/components/Toolbar";
import { StatusBar } from "@/components/StatusBar";
import { loggerPrefix } from "@/lib/const";

import "./styles.css";

/**
 * LoadingText
 *
 * Displays a muted "Loading..." text, typically used in skeleton or ghost rows to indicate loading state.
 */
const LoadingText = () => {
  return <span className="text-muted fw-semibold">Loading...</span>;
};

/**
 * TableHeader
 *
 * Renders the table header row for the vectorsearch list, including column titles for all displayed fields.
 */
const TableHeader = () => {
  return (
    <thead className="table-light border-bottom-2">
      <tr className="">
        <th className=" p-1">Name</th>
        <th className="d-none d-lg-table-cell width-100">Created</th>
        <th className="d-none d-lg-table-cell width-100">Updated</th>
        <th className="">Description</th>
        <th className="">Vectorstore</th>
        <th className="d-none d-lg-table-cell">Search Type</th>
        <th className="d-none d-md-table-cell">Status</th>
        <th className="">Operations</th>
      </tr>
    </thead>
  );
};

/**
 * VectorsearchRow
 *
 * Renders a single vectorsearch as a table row, displaying its details and action toolbar.
 *
 * @param vectorsearch - The vectorsearch object to display.
 * @param sessionContext - Session context for actions.
 * @param onRequery - Callback to refresh vectorsearch data after an action.
 */
const VectorsearchRow = React.memo(function VectorsearchRow({
  vectorsearch,
  sessionContext,
  onRequery,
}: {
  vectorsearch: Vectorsearch;
  sessionContext: SessionContext;
  onRequery: () => void;
}) {
  const CreatedDate = ({ date }: { date: string }) => {
    return <span>{formatDateTime(date, "date")}</span>;
  };

  const UpdatedDate = ({ date, createdAt }: { date: string | null; createdAt: string }) => {
    return <span>{formatDateTime(date, "relative", createdAt)}</span>;
  };

  return (
    <tr className="" key={vectorsearch.id}>
      {/* Name */}
      <td className="p-1 m-0">
        <a href={vectorsearch.manifestUrl}>{vectorsearch.name}</a>
      </td>
      {/* Created Date */}
      <td className="d-none d-lg-table-cell width-100">
        <CreatedDate date={vectorsearch.createdAt} />
      </td>
      {/* Updated Date */}
      <td className="d-none d-lg-table-cell width-100">
        <UpdatedDate date={vectorsearch.updatedAt} createdAt={vectorsearch.createdAt} />
      </td>
      {/* Description */}
      <td className="">{vectorsearch.description}</td>
      <td className="">{vectorsearch.vectorstore}</td>
      <td className="">{vectorsearch.searchType}</td>
      {/* Status */}
      <td className="d-none d-md-table-cell ">
        <StatusBar vectorsearch={vectorsearch} />
      </td>
      {/* Actions */}
      <td className="text-end ">
        <Toolbar sessionContext={sessionContext} vectorsearch={vectorsearch} onRequery={onRequery} />
      </td>
    </tr>
  );
});

/**
 * VectorsearchRowGhost
 *
 * A skeleton row component to display while vectorsearch data is loading.
 * It mimics the structure of a regular VectorsearchRow but with placeholder content.
 */
const VectorsearchRowGhost = React.memo(function VectorsearchRowGhost() {
  console.debug(`${loggerPrefix} Rendering VectorsearchRowGhost`);
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
      {/* Vectorstore */}
      <td className="d-none d-xl-table-cell"></td>
      {/* searchType */}
      <td className="d-none d-xl-table-cell"></td>
      {/* Status */}
      <td className="d-none d-md-table-cell "></td>
      {/* Actions */}
      <td className="text-end "></td>
    </tr>
  );
});

/**
 * VectorsearchRowGhosts
 *
 * Renders a specified number of skeleton (ghost) rows to indicate loading state in the vectorsearch list.
 *
 * @param count - Number of skeleton rows to render.
 */
const VectorsearchRowGhosts = React.memo(function VectorsearchRowGhosts({ count }: { count: number }) {
  console.debug(`${loggerPrefix} Rendering VectorsearchRowGhosts with count: ${count}`);
  return (
    <>
      {Array.from({ length: count }).map((_, idx) => (
        <VectorsearchRowGhost key={idx} />
      ))}
    </>
  );
});

/**
 * ChunkedRows
 *
 * Incrementally renders vectorsearch rows in chunks to avoid UI blocking.
 * Uses requestIdleCallback (if available) or setTimeout as a fallback to schedule rendering.
 *
 * @param vectorsearchs - Array of vectorsearch objects to render.
 * @param sessionContext - Session context for actions.
 * @param onRequery - Callback to refresh vectorsearch data.
 * @param chunkSize - Number of rows to render per chunk (default: 5).
 */
function ChunkedRows({
  vectorsearchs,
  sessionContext,
  onRequery,
  chunkSize = 5,
}: {
  vectorsearchs: Vectorsearch[];
  sessionContext: SessionContext;
  onRequery: () => void;
  chunkSize?: number;
}) {
  const [visibleCount, setVisibleCount] = useState(chunkSize);

  const schedule = window.requestIdleCallback || ((cb: Function) => setTimeout(cb, 0));
  const cancel = window.cancelIdleCallback || clearTimeout;

  useEffect(() => {
    let idleId: any = null;
    if (visibleCount < vectorsearchs.length) {
      idleId = schedule(() => {
        setVisibleCount((c) => Math.min(c + chunkSize, vectorsearchs.length));
      });
      return () => cancel(idleId);
    }
  }, [visibleCount, vectorsearchs.length, chunkSize]);
  return (
    <>
      {vectorsearchs.slice(0, visibleCount).map((vectorsearch) => (
        <VectorsearchRow key={vectorsearch.id} vectorsearch={vectorsearch} sessionContext={sessionContext} onRequery={onRequery} />
      ))}
    </>
  );
}

/**
 * ListView
 *
 * Main component for displaying a responsive, table-based list of vectorsearch resources.
 * Handles loading state with skeleton rows and incremental rendering for large lists.
 *
 * @param isLoading - Whether the vectorsearch data is loading (shows skeleton rows if true).
 * @param ghostRows - Number of skeleton rows to display while loading.
 * @param sessionContext - Authentication and API context for actions.
 * @param vectorsearchs - Array of vectorsearch objects to display.
 * @param onRequery - Callback to refresh vectorsearch data.
 */
export function ListView({ isLoading, ghostRows, sessionContext, objects, onRequery }: VectorsearchListViewProps) {
  console.debug(
    `${loggerPrefix} ListView() Rendering ListView - {isLoading: ${isLoading}, ghostRows: ${ghostRows}, objects length: ${Array.isArray(objects) ? objects.length : "N/A"}}`,
  );
  console.debug(`${loggerPrefix} SessionContext:`, sessionContext);
  console.debug(`${loggerPrefix} Objects:`, objects);
  return (
    <div className="table-responsive vectorsearch-list-table-wrap ps-3 pe-3">
      <table className="table table-striped table-hover align-middle border">
        <TableHeader />
        <tbody>
          {isLoading ? (
            <VectorsearchRowGhosts count={ghostRows} />
          ) : (
            <ChunkedRows vectorsearchs={objects} sessionContext={sessionContext} onRequery={onRequery} />
          )}
        </tbody>
      </table>
    </div>
  );
}

export default ListView;

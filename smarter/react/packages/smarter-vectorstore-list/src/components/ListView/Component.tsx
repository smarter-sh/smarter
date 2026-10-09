/**
 * ListView
 *
 * Renders a responsive, table-based list of vectorstore resources with key details and actions.
 * Features:
 * - Displays vectorstore information in a styled table with columns for name, dates, provider, model, vectorstores, status, and actions.
 * - Integrates Toolbar for per-vectorstore actions (open, edit, clone, rename, delete).
 * - Formats dates and status using shared utilities.
 * - Shows skeleton (ghost) rows while loading, and supports incremental rendering for large lists.
 *
 * Props:
 * @param isLoading - Whether the vectorstore data is loading (shows skeleton rows if true).
 * @param ghostRows - Number of skeleton rows to display while loading.
 * @param sessionContext - Authentication and API context for actions.
 * @param vectorstores - Array of vectorstore objects to display.
 * @param onRequery - Callback to refresh vectorstore data.
 *
 * Usage:
 * <ListView
 *   sessionContext={sessionContext}
 *   vectorstores={vectorstores}
 *   isLoading={isLoading}
 *   ghostRows={ghostRows}
 *   onRequery={onRequery}
 * />
 *
 * Intended for views where vectorstores are presented in a list/table format.
 */
import React, { useState, useEffect } from "react";

import { formatDateTime, Loading, SortableHeader } from "@smarter/common";
import type { SessionContext, Sorting } from "@smarter/common";

import type { Vectorstore, VectorstoreListViewProps } from "@/lib/Types";
import { Toolbar } from "@/components/Toolbar";
import { StatusBar } from "@/components/StatusBar";
import { loggerPrefix } from "@/lib/const";
import { databaseLabel, formatCount } from "@/lib/format";

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
 * Renders the table header row for the vectorstore list, including column titles for all displayed fields.
 * Its sortable columns sort the list, with the list api (see SortableHeader).
 */
const TableHeader = ({ sorting }: { sorting?: Sorting }) => {
  return (
    <thead className="table-light border-bottom-2">
      <tr className="">
        <SortableHeader column="name" sorting={sorting} className=" p-1">
          Name
        </SortableHeader>
        <SortableHeader column="database" sorting={sorting} className="d-none d-md-table-cell">
          Database
        </SortableHeader>
        <th className="">Status</th>
        <SortableHeader column="vectorCount" sorting={sorting} className="d-none d-lg-table-cell text-end">
          Vectors
        </SortableHeader>
        <th className="d-none d-lg-table-cell text-end">Documents</th>
        <SortableHeader column="updatedAt" sorting={sorting} className="d-none d-lg-table-cell width-100">
          Updated
        </SortableHeader>
        <th className="">Operations</th>
      </tr>
    </thead>
  );
};

/**
 * UpdatedDate
 *
 * Format a row's last update, relative to its creation.
 */
const UpdatedDate = ({ date, createdAt }: { date: string; createdAt: string }) => {
  return <span>{formatDateTime(date, "relative", createdAt)}</span>;
};

/**
 * VectorstoreRow
 *
 * Renders a single vectorstore as a table row, displaying its details and action toolbar.
 *
 * @param vectorstore - The vectorstore object to display.
 * @param sessionContext - Session context for actions.
 * @param onRequery - Callback to refresh vectorstore data after an action.
 */
const VectorstoreRow = React.memo(function VectorstoreRow({
  vectorstore,
  sessionContext,
  onRequery,
}: {
  vectorstore: Vectorstore;
  sessionContext: SessionContext;
  onRequery: () => void;
}) {
  return (
    <tr className="" key={vectorstore.id}>
      {/* Name */}
      <td className="p-1 m-0">
        <a href={vectorstore.manifestUrl}>{vectorstore.name}</a>
        <div className="text-muted fs-8">{vectorstore.description}</div>
      </td>
      {/* Database */}
      <td className="d-none d-md-table-cell">{databaseLabel(vectorstore)}</td>
      {/* Status */}
      <td className="">
        <StatusBar vectorstore={vectorstore} />
      </td>
      {/* Vectors */}
      <td className="d-none d-lg-table-cell text-end">{formatCount(vectorstore.vectorCount)}</td>
      {/* Documents */}
      <td className="d-none d-lg-table-cell text-end">{formatCount(vectorstore.documentCount)}</td>
      {/* Updated Date */}
      <td className="d-none d-lg-table-cell width-100">
        <UpdatedDate date={vectorstore.updatedAt} createdAt={vectorstore.createdAt} />
      </td>
      {/* Actions */}
      <td className="text-end ">
        <Toolbar sessionContext={sessionContext} vectorstore={vectorstore} onRequery={onRequery} />
      </td>
    </tr>
  );
});

/**
 * VectorstoreRowGhost
 *
 * A skeleton row component to display while vectorstore data is loading.
 * It mimics the structure of a regular VectorstoreRow but with placeholder content.
 */
const VectorstoreRowGhost = React.memo(function VectorstoreRowGhost() {
  console.debug(`${loggerPrefix} Rendering VectorstoreRowGhost`);
  return (
    <tr className="ghost">
      <td className="p-1 m-0">
        <Loading />
      </td>
      <td className="d-none d-md-table-cell">
        <LoadingText />
      </td>
      <td className=""></td>
      <td className="d-none d-lg-table-cell"></td>
      <td className="d-none d-lg-table-cell"></td>
      <td className="d-none d-lg-table-cell width-100"></td>
      <td className="text-end "></td>
    </tr>
  );
});

/**
 * VectorstoreRowGhosts
 *
 * Renders a specified number of skeleton (ghost) rows to indicate loading state in the vectorstore list.
 *
 * @param count - Number of skeleton rows to render.
 */
const VectorstoreRowGhosts = React.memo(function VectorstoreRowGhosts({ count }: { count: number }) {
  console.debug(`${loggerPrefix} Rendering VectorstoreRowGhosts with count: ${count}`);
  return (
    <>
      {Array.from({ length: count }).map((_, idx) => (
        <VectorstoreRowGhost key={idx} />
      ))}
    </>
  );
});

/**
 * ChunkedRows
 *
 * Incrementally renders vectorstore rows in chunks to avoid UI blocking.
 * Uses requestIdleCallback (if available) or setTimeout as a fallback to schedule rendering.
 *
 * @param vectorstores - Array of vectorstore objects to render.
 * @param sessionContext - Session context for actions.
 * @param onRequery - Callback to refresh vectorstore data.
 * @param chunkSize - Number of rows to render per chunk (default: 5).
 */
function ChunkedRows({
  vectorstores,
  sessionContext,
  onRequery,
  chunkSize = 5,
}: {
  vectorstores: Vectorstore[];
  sessionContext: SessionContext;
  onRequery: () => void;
  chunkSize?: number;
}) {
  const [visibleCount, setVisibleCount] = useState(chunkSize);

  useEffect(() => {
    if (visibleCount >= vectorstores.length) return;
    const next = () => setVisibleCount((c) => Math.min(c + chunkSize, vectorstores.length));
    if (window.requestIdleCallback) {
      const idleId = window.requestIdleCallback(next);
      return () => window.cancelIdleCallback(idleId);
    }
    const timeoutId = setTimeout(next, 0);
    return () => clearTimeout(timeoutId);
  }, [visibleCount, vectorstores.length, chunkSize]);
  return (
    <>
      {vectorstores.slice(0, visibleCount).map((vectorstore) => (
        <VectorstoreRow
          key={vectorstore.id}
          vectorstore={vectorstore}
          sessionContext={sessionContext}
          onRequery={onRequery}
        />
      ))}
    </>
  );
}

/**
 * ListView
 *
 * Main component for displaying a responsive, table-based list of vectorstore resources.
 * Handles loading state with skeleton rows and incremental rendering for large lists.
 *
 * @param isLoading - Whether the vectorstore data is loading (shows skeleton rows if true).
 * @param ghostRows - Number of skeleton rows to display while loading.
 * @param sessionContext - Authentication and API context for actions.
 * @param vectorstores - Array of vectorstore objects to display.
 * @param onRequery - Callback to refresh vectorstore data.
 * @param sorting - The sort of the list, which its sortable column headers change.
 */
export function ListView({
  isLoading,
  ghostRows,
  sessionContext,
  objects,
  onRequery,
  sorting,
}: VectorstoreListViewProps) {
  console.debug(
    `${loggerPrefix} ListView() Rendering ListView - {isLoading: ${isLoading}, ghostRows: ${ghostRows}, objects length: ${Array.isArray(objects) ? objects.length : "N/A"}}`,
  );
  return (
    <div className="table-responsive vectorstore-list-table-wrap ps-3 pe-3">
      <table className="table table-striped table-hover align-middle border">
        <TableHeader sorting={sorting} />
        <tbody>
          {isLoading ? (
            <VectorstoreRowGhosts count={ghostRows} />
          ) : (
            <ChunkedRows vectorstores={objects} sessionContext={sessionContext} onRequery={onRequery} />
          )}
        </tbody>
      </table>
    </div>
  );
}

export default ListView;

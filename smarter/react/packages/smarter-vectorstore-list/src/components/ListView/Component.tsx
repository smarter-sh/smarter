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

import { formatDateTime, Loading } from "@smarter/common";
import type { SessionContext } from "@smarter/common";

import type { Vectorestore, VectorestoreListViewProps } from "@/lib/Types";
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
 * Renders the table header row for the vectorstore list, including column titles for all displayed fields.
 */
const TableHeader = () => {
  return (
    <thead className="table-light border-bottom-2">
      <tr className="">
        <th className=" p-1">Name</th>
        <th className="d-none d-lg-table-cell width-100">Created</th>
        <th className="d-none d-lg-table-cell width-100">Updated</th>
        <th className="">Description</th>
        <th className="d-none d-md-table-cell">Status</th>
        <th className="">Operations</th>
      </tr>
    </thead>
  );
};

/**
 * VectorestoreRow
 *
 * Renders a single vectorstore as a table row, displaying its details and action toolbar.
 *
 * @param vectorstore - The vectorstore object to display.
 * @param sessionContext - Session context for actions.
 * @param onRequery - Callback to refresh vectorstore data after an action.
 */
const VectorestoreRow = React.memo(function VectorestoreRow({
  vectorstore,
  sessionContext,
  onRequery,
}: {
  vectorstore: Vectorestore;
  sessionContext: SessionContext;
  onRequery: () => void;
}) {
  const CreatedDate = ({ date }: { date: string }) => {
    return <span>{formatDateTime(date, "date")}</span>;
  };

  const UpdatedDate = ({ date, createdAt }: { date: string; createdAt: string }) => {
    return <span>{formatDateTime(date, "relative", createdAt)}</span>;
  };

  return (
    <tr className="" key={vectorstore.id}>
      {/* Name */}
      <td className="p-1 m-0">
        <a href={vectorstore.manifestUrl}>{vectorstore.name}</a>
      </td>
      {/* Created Date */}
      <td className="d-none d-lg-table-cell width-100">
        <CreatedDate date={vectorstore.createdAt} />
      </td>
      {/* Updated Date */}
      <td className="d-none d-lg-table-cell width-100">
        <UpdatedDate date={vectorstore.updatedAt} createdAt={vectorstore.createdAt} />
      </td>
      {/* Description */}
      <td className="">{vectorstore.description}</td>
      {/* Status */}
      <td className="d-none d-md-table-cell ">
        <StatusBar vectorstore={vectorstore} />
      </td>
      {/* Actions */}
      <td className="text-end ">
        <Toolbar sessionContext={sessionContext} vectorstore={vectorstore} onRequery={onRequery} />
      </td>
    </tr>
  );
});

/**
 * VectorestoreRowGhost
 *
 * A skeleton row component to display while vectorstore data is loading.
 * It mimics the structure of a regular VectorestoreRow but with placeholder content.
 */
const VectorestoreRowGhost = React.memo(function VectorestoreRowGhost() {
  console.debug(`${loggerPrefix} Rendering VectorestoreRowGhost`);
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
 * VectorestoreRowGhosts
 *
 * Renders a specified number of skeleton (ghost) rows to indicate loading state in the vectorstore list.
 *
 * @param count - Number of skeleton rows to render.
 */
const VectorestoreRowGhosts = React.memo(function VectorestoreRowGhosts({ count }: { count: number }) {
  console.debug(`${loggerPrefix} Rendering VectorestoreRowGhosts with count: ${count}`);
  return (
    <>
      {Array.from({ length: count }).map((_, idx) => (
        <VectorestoreRowGhost key={idx} />
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
  vectorstores: Vectorestore[];
  sessionContext: SessionContext;
  onRequery: () => void;
  chunkSize?: number;
}) {
  const [visibleCount, setVisibleCount] = useState(chunkSize);

  const schedule = window.requestIdleCallback || ((cb: Function) => setTimeout(cb, 0));
  const cancel = window.cancelIdleCallback || clearTimeout;

  useEffect(() => {
    let idleId: any = null;
    if (visibleCount < vectorstores.length) {
      idleId = schedule(() => {
        setVisibleCount((c) => Math.min(c + chunkSize, vectorstores.length));
      });
      return () => cancel(idleId);
    }
  }, [visibleCount, vectorstores.length, chunkSize]);
  return (
    <>
      {vectorstores.slice(0, visibleCount).map((vectorstore) => (
        <VectorestoreRow key={vectorstore.id} vectorstore={vectorstore} sessionContext={sessionContext} onRequery={onRequery} />
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
 */
export function ListView({ isLoading, ghostRows, sessionContext, objects, onRequery }: VectorestoreListViewProps) {
  console.debug(
    `${loggerPrefix} ListView() Rendering ListView - {isLoading: ${isLoading}, ghostRows: ${ghostRows}, objects length: ${Array.isArray(objects) ? objects.length : "N/A"}}`,
  );
  return (
    <div className="table-responsive vectorstore-list-table-wrap ps-3 pe-3">
      <table className="table table-striped table-hover align-middle border">
        <TableHeader />
        <tbody>
          {isLoading ? (
            <VectorestoreRowGhosts count={ghostRows} />
          ) : (
            <ChunkedRows vectorstores={objects} sessionContext={sessionContext} onRequery={onRequery} />
          )}
        </tbody>
      </table>
    </div>
  );
}

export default ListView;

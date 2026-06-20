/**
 * ListView
 *
 * Renders a responsive, table-based list of connection resources with key details and actions.
 * Features:
 * - Displays connection information in a styled table with columns for name, dates, provider, model, connections, status, and actions.
 * - Integrates Toolbar for per-connection actions (open, edit, clone, rename, delete).
 * - Formats dates and status using shared utilities.
 * - Shows skeleton (ghost) rows while loading, and supports incremental rendering for large lists.
 *
 * Props:
 * @param isLoading - Whether the connection data is loading (shows skeleton rows if true).
 * @param ghostRows - Number of skeleton rows to display while loading.
 * @param sessionContext - Authentication and API context for actions.
 * @param connections - Array of connection objects to display.
 * @param onRequery - Callback to refresh connection data.
 *
 * Usage:
 * <ListView
 *   sessionContext={sessionContext}
 *   connections={connections}
 *   isLoading={isLoading}
 *   ghostRows={ghostRows}
 *   onRequery={onRequery}
 * />
 *
 * Intended for views where connections are presented in a list/table format.
 */
import React, { useState, useEffect } from "react";

import { Loading, formatDateTime } from "@smarter/common";
import type { SessionContext } from "@smarter/common";

import type { Connection, ConnectionListViewProps } from "@/lib/Types";
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
 * Renders the table header row for the connection list, including column titles for all displayed fields.
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
 * ConnectionRow
 *
 * Renders a single connection as a table row, displaying its details and action toolbar.
 *
 * @param connection - The connection object to display.
 * @param sessionContext - Session context for actions.
 * @param onRequery - Callback to refresh connection data after an action.
 */
const ConnectionRow = React.memo(function ConnectionRow({
  connection,
  sessionContext,
  onRequery,
}: {
  connection: Connection;
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
    <tr className="" key={connection.id}>
      {/* Name */}
      <td className="p-1 m-0">
        <a href={connection.manifestUrl}>{connection.name}</a>
      </td>
      {/* Created Date */}
      <td className="d-none d-lg-table-cell width-100">
        <CreatedDate date={connection.createdAt} />
      </td>
      {/* Updated Date */}
      <td className="d-none d-lg-table-cell width-100">
        <UpdatedDate date={connection.updatedAt} createdAt={connection.createdAt} />
      </td>
      {/* Description */}
      <td className="">{connection.description}</td>
      {/* Status */}
      <td className="d-none d-md-table-cell ">
        <StatusBar connection={connection} />
      </td>
      {/* Actions */}
      <td className="text-end ">
        <Toolbar sessionContext={sessionContext} connection={connection} onRequery={onRequery} />
      </td>
    </tr>
  );
});

/**
 * ConnectionRowGhost
 *
 * A skeleton row component to display while connection data is loading.
 * It mimics the structure of a regular ConnectionRow but with placeholder content.
 */
const ConnectionRowGhost = React.memo(function ConnectionRowGhost() {
  console.debug(`${loggerPrefix} Rendering ConnectionRowGhost`);
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
 * ConnectionRowGhosts
 *
 * Renders a specified number of skeleton (ghost) rows to indicate loading state in the connection list.
 *
 * @param count - Number of skeleton rows to render.
 */
const ConnectionRowGhosts = React.memo(function ConnectionRowGhosts({ count }: { count: number }) {
  console.debug(`${loggerPrefix} Rendering ConnectionRowGhosts with count: ${count}`);
  return (
    <>
      {Array.from({ length: count }).map((_, idx) => (
        <ConnectionRowGhost key={idx} />
      ))}
    </>
  );
});

/**
 * ChunkedRows
 *
 * Incrementally renders connection rows in chunks to avoid UI blocking.
 * Uses requestIdleCallback (if available) or setTimeout as a fallback to schedule rendering.
 *
 * @param connections - Array of connection objects to render.
 * @param sessionContext - Session context for actions.
 * @param onRequery - Callback to refresh connection data.
 * @param chunkSize - Number of rows to render per chunk (default: 5).
 */
function ChunkedRows({
  connections,
  sessionContext,
  onRequery,
  chunkSize = 5,
}: {
  connections: Connection[];
  sessionContext: SessionContext;
  onRequery: () => void;
  chunkSize?: number;
}) {
  const [visibleCount, setVisibleCount] = useState(chunkSize);

  const schedule = window.requestIdleCallback || ((cb: Function) => setTimeout(cb, 0));
  const cancel = window.cancelIdleCallback || clearTimeout;

  useEffect(() => {
    let idleId: any = null;
    if (visibleCount < connections.length) {
      idleId = schedule(() => {
        setVisibleCount((c) => Math.min(c + chunkSize, connections.length));
      });
      return () => cancel(idleId);
    }
  }, [visibleCount, connections.length, chunkSize]);
  return (
    <>
      {connections.slice(0, visibleCount).map((connection) => (
        <ConnectionRow key={connection.id} connection={connection} sessionContext={sessionContext} onRequery={onRequery} />
      ))}
    </>
  );
}

/**
 * ListView
 *
 * Main component for displaying a responsive, table-based list of connection resources.
 * Handles loading state with skeleton rows and incremental rendering for large lists.
 *
 * @param isLoading - Whether the connection data is loading (shows skeleton rows if true).
 * @param ghostRows - Number of skeleton rows to display while loading.
 * @param sessionContext - Authentication and API context for actions.
 * @param connections - Array of connection objects to display.
 * @param onRequery - Callback to refresh connection data.
 */
export function ListView({ isLoading, ghostRows, sessionContext, objects, onRequery }: ConnectionListViewProps) {
  console.debug(
    `${loggerPrefix} ListView() Rendering ListView - {isLoading: ${isLoading}, ghostRows: ${ghostRows}, objects length: ${Array.isArray(objects) ? objects.length : "N/A"}}`,
  );
  return (
    <div className="table-responsive connection-list-table-wrap ps-3 pe-3">
      <table className="table table-striped table-hover align-middle border">
        <TableHeader />
        <tbody>
          {isLoading ? (
            <ConnectionRowGhosts count={ghostRows} />
          ) : (
            <ChunkedRows connections={objects} sessionContext={sessionContext} onRequery={onRequery} />
          )}
        </tbody>
      </table>
    </div>
  );
}

export default ListView;

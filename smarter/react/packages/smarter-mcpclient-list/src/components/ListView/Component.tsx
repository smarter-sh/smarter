/**
 * ListView
 *
 * Renders a responsive, table-based list of mcpclient resources with key details and actions.
 * Features:
 * - Displays mcpclient information in a styled table with columns for name, dates, mcpclient, model, mcpclients, status, and actions.
 * - Integrates Toolbar for per-mcpclient actions (open, edit, clone, rename, delete).
 * - Formats dates and status using shared utilities.
 * - Shows skeleton (ghost) rows while loading, and supports incremental rendering for large lists.
 *
 * Props:
 * @param isLoading - Whether the mcpclient data is loading (shows skeleton rows if true).
 * @param ghostRows - Number of skeleton rows to display while loading.
 * @param sessionContext - Authentication and API context for actions.
 * @param mcpclients - Array of mcpclient objects to display.
 * @param onRequery - Callback to refresh mcpclient data.
 *
 * Usage:
 * <ListView
 *   sessionContext={sessionContext}
 *   mcpclients={mcpclients}
 *   isLoading={isLoading}
 *   ghostRows={ghostRows}
 *   onRequery={onRequery}
 * />
 *
 * Intended for views where mcpclients are presented in a list/table format.
 */
import React, { useState, useEffect } from "react";

import { Loading, formatDateTime } from "@smarter/common";
import type { SessionContext } from "@smarter/common";

import type { MCPClient, MCPClientListViewProps } from "@/lib/Types";
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
 * Renders the table header row for the mcpclient list, including column titles for all displayed fields.
 */
const TableHeader = () => {
  return (
    <thead className="table-light border-bottom-2">
      <tr className="">
        <th className=" p-1">Name</th>
        <th className="d-none d-lg-table-cell width-100">Created</th>
        <th className="d-none d-lg-table-cell width-100">Updated</th>
        <th className="">Description</th>
        <th className="">Active</th>
        <th className="d-none d-lg-table-cell">Priority</th>
        <th className="d-none d-md-table-cell">Status</th>
        <th className="">Operations</th>
      </tr>
    </thead>
  );
};

/**
 * MCPClientRow
 *
 * Renders a single mcpclient as a table row, displaying its details and action toolbar.
 *
 * @param mcpclient - The mcpclient object to display.
 * @param sessionContext - Session context for actions.
 * @param onRequery - Callback to refresh mcpclient data after an action.
 */
const MCPClientRow = React.memo(function MCPClientRow({
  mcpclient,
  sessionContext,
  onRequery,
}: {
  mcpclient: MCPClient;
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
    <tr className="" key={mcpclient.id}>
      {/* Name */}
      <td className="p-1 m-0">
        <a href={mcpclient.manifestUrl}>{mcpclient.name}</a>
      </td>
      {/* Created Date */}
      <td className="d-none d-lg-table-cell width-100">
        <CreatedDate date={mcpclient.createdAt} />
      </td>
      {/* Updated Date */}
      <td className="d-none d-lg-table-cell width-100">
        <UpdatedDate date={mcpclient.updatedAt} createdAt={mcpclient.createdAt} />
      </td>
      {/* Description */}
      <td className="">{mcpclient.description}</td>
      <td className="">{mcpclient.isActive}</td>
      <td className="">{mcpclient.priority}</td>
      {/* Status */}
      <td className="d-none d-md-table-cell ">
        <StatusBar mcpclient={mcpclient} />
      </td>
      {/* Actions */}
      <td className="text-end ">
        <Toolbar sessionContext={sessionContext} mcpclient={mcpclient} onRequery={onRequery} />
      </td>
    </tr>
  );
});

/**
 * MCPClientRowGhost
 *
 * A skeleton row component to display while mcpclient data is loading.
 * It mimics the structure of a regular MCPClientRow but with placeholder content.
 */
const MCPClientRowGhost = React.memo(function MCPClientRowGhost() {
  console.debug(`${loggerPrefix} Rendering MCPClientRowGhost`);
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
      {/* isActive */}
      <td className="d-none d-xl-table-cell"></td>
      {/* priority */}
      <td className="d-none d-xl-table-cell"></td>
      {/* Status */}
      <td className="d-none d-md-table-cell "></td>
      {/* Actions */}
      <td className="text-end "></td>
    </tr>
  );
});

/**
 * MCPClientRowGhosts
 *
 * Renders a specified number of skeleton (ghost) rows to indicate loading state in the mcpclient list.
 *
 * @param count - Number of skeleton rows to render.
 */
const MCPClientRowGhosts = React.memo(function MCPClientRowGhosts({ count }: { count: number }) {
  console.debug(`${loggerPrefix} Rendering MCPClientRowGhosts with count: ${count}`);
  return (
    <>
      {Array.from({ length: count }).map((_, idx) => (
        <MCPClientRowGhost key={idx} />
      ))}
    </>
  );
});

/**
 * ChunkedRows
 *
 * Incrementally renders mcpclient rows in chunks to avoid UI blocking.
 * Uses requestIdleCallback (if available) or setTimeout as a fallback to schedule rendering.
 *
 * @param mcpclients - Array of mcpclient objects to render.
 * @param sessionContext - Session context for actions.
 * @param onRequery - Callback to refresh mcpclient data.
 * @param chunkSize - Number of rows to render per chunk (default: 5).
 */
function ChunkedRows({
  mcpclients,
  sessionContext,
  onRequery,
  chunkSize = 5,
}: {
  mcpclients: MCPClient[];
  sessionContext: SessionContext;
  onRequery: () => void;
  chunkSize?: number;
}) {
  const [visibleCount, setVisibleCount] = useState(chunkSize);

  const schedule = window.requestIdleCallback || ((cb: Function) => setTimeout(cb, 0));
  const cancel = window.cancelIdleCallback || clearTimeout;

  useEffect(() => {
    let idleId: any = null;
    if (visibleCount < mcpclients.length) {
      idleId = schedule(() => {
        setVisibleCount((c) => Math.min(c + chunkSize, mcpclients.length));
      });
      return () => cancel(idleId);
    }
  }, [visibleCount, mcpclients.length, chunkSize]);
  return (
    <>
      {mcpclients.slice(0, visibleCount).map((mcpclient) => (
        <MCPClientRow key={mcpclient.id} mcpclient={mcpclient} sessionContext={sessionContext} onRequery={onRequery} />
      ))}
    </>
  );
}

/**
 * ListView
 *
 * Main component for displaying a responsive, table-based list of mcpclient resources.
 * Handles loading state with skeleton rows and incremental rendering for large lists.
 *
 * @param isLoading - Whether the mcpclient data is loading (shows skeleton rows if true).
 * @param ghostRows - Number of skeleton rows to display while loading.
 * @param sessionContext - Authentication and API context for actions.
 * @param mcpclients - Array of mcpclient objects to display.
 * @param onRequery - Callback to refresh mcpclient data.
 */
export function ListView({ isLoading, ghostRows, sessionContext, objects, onRequery }: MCPClientListViewProps) {
  console.debug(
    `${loggerPrefix} ListView() Rendering ListView - {isLoading: ${isLoading}, ghostRows: ${ghostRows}, objects length: ${Array.isArray(objects) ? objects.length : "N/A"}}`,
  );
  console.debug(`${loggerPrefix} SessionContext:`, sessionContext);
  console.debug(`${loggerPrefix} Objects:`, objects);
  return (
    <div className="table-responsive mcpclient-list-table-wrap ps-3 pe-3">
      <table className="table table-striped table-hover align-middle border">
        <TableHeader />
        <tbody>
          {isLoading ? (
            <MCPClientRowGhosts count={ghostRows} />
          ) : (
            <ChunkedRows mcpclients={objects} sessionContext={sessionContext} onRequery={onRequery} />
          )}
        </tbody>
      </table>
    </div>
  );
}

export default ListView;

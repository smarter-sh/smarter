/**
 * ListView
 *
 * Renders a responsive, table-based list of orchestrator resources with key details and actions.
 * Features:
 * - Displays orchestrator information in a styled table with columns for name, dates, orchestrator, model, orchestrators, status, and actions.
 * - Integrates Toolbar for per-orchestrator actions (open, edit, clone, rename, delete).
 * - Formats dates and status using shared utilities.
 * - Shows skeleton (ghost) rows while loading, and supports incremental rendering for large lists.
 *
 * Props:
 * @param isLoading - Whether the orchestrator data is loading (shows skeleton rows if true).
 * @param ghostRows - Number of skeleton rows to display while loading.
 * @param sessionContext - Authentication and API context for actions.
 * @param orchestrators - Array of orchestrator objects to display.
 * @param onRequery - Callback to refresh orchestrator data.
 *
 * Usage:
 * <ListView
 *   sessionContext={sessionContext}
 *   orchestrators={orchestrators}
 *   isLoading={isLoading}
 *   ghostRows={ghostRows}
 *   onRequery={onRequery}
 * />
 *
 * Intended for views where orchestrators are presented in a list/table format.
 */
import React, { useState, useEffect } from "react";

import { Loading, formatDateTime } from "@smarter/common";
import type { SessionContext } from "@smarter/common";

import type { Orchestrator, OrchestratorListViewProps } from "@/lib/Types";
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
 * Renders the table header row for the orchestrator list, including column titles for all displayed fields.
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
        <th className="d-none d-lg-table-cell">Strategy</th>
        <th className="d-none d-md-table-cell">Status</th>
        <th className="">Operations</th>
      </tr>
    </thead>
  );
};

/**
 * OrchestratorRow
 *
 * Renders a single orchestrator as a table row, displaying its details and action toolbar.
 *
 * @param orchestrator - The orchestrator object to display.
 * @param sessionContext - Session context for actions.
 * @param onRequery - Callback to refresh orchestrator data after an action.
 */
const OrchestratorRow = React.memo(function OrchestratorRow({
  orchestrator,
  sessionContext,
  onRequery,
}: {
  orchestrator: Orchestrator;
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
    <tr className="" key={orchestrator.id}>
      {/* Name */}
      <td className="p-1 m-0">
        <a href={orchestrator.manifestUrl}>{orchestrator.name}</a>
      </td>
      {/* Created Date */}
      <td className="d-none d-lg-table-cell width-100">
        <CreatedDate date={orchestrator.createdAt} />
      </td>
      {/* Updated Date */}
      <td className="d-none d-lg-table-cell width-100">
        <UpdatedDate date={orchestrator.updatedAt} createdAt={orchestrator.createdAt} />
      </td>
      {/* Description */}
      <td className="">{orchestrator.description}</td>
      <td className="">{orchestrator.isActive}</td>
      <td className="">{orchestrator.strategy}</td>
      {/* Status */}
      <td className="d-none d-md-table-cell ">
        <StatusBar orchestrator={orchestrator} />
      </td>
      {/* Actions */}
      <td className="text-end ">
        <Toolbar sessionContext={sessionContext} orchestrator={orchestrator} onRequery={onRequery} />
      </td>
    </tr>
  );
});

/**
 * OrchestratorRowGhost
 *
 * A skeleton row component to display while orchestrator data is loading.
 * It mimics the structure of a regular OrchestratorRow but with placeholder content.
 */
const OrchestratorRowGhost = React.memo(function OrchestratorRowGhost() {
  console.debug(`${loggerPrefix} Rendering OrchestratorRowGhost`);
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
      {/* strategy */}
      <td className="d-none d-xl-table-cell"></td>
      {/* Status */}
      <td className="d-none d-md-table-cell "></td>
      {/* Actions */}
      <td className="text-end "></td>
    </tr>
  );
});

/**
 * OrchestratorRowGhosts
 *
 * Renders a specified number of skeleton (ghost) rows to indicate loading state in the orchestrator list.
 *
 * @param count - Number of skeleton rows to render.
 */
const OrchestratorRowGhosts = React.memo(function OrchestratorRowGhosts({ count }: { count: number }) {
  console.debug(`${loggerPrefix} Rendering OrchestratorRowGhosts with count: ${count}`);
  return (
    <>
      {Array.from({ length: count }).map((_, idx) => (
        <OrchestratorRowGhost key={idx} />
      ))}
    </>
  );
});

/**
 * ChunkedRows
 *
 * Incrementally renders orchestrator rows in chunks to avoid UI blocking.
 * Uses requestIdleCallback (if available) or setTimeout as a fallback to schedule rendering.
 *
 * @param orchestrators - Array of orchestrator objects to render.
 * @param sessionContext - Session context for actions.
 * @param onRequery - Callback to refresh orchestrator data.
 * @param chunkSize - Number of rows to render per chunk (default: 5).
 */
function ChunkedRows({
  orchestrators,
  sessionContext,
  onRequery,
  chunkSize = 5,
}: {
  orchestrators: Orchestrator[];
  sessionContext: SessionContext;
  onRequery: () => void;
  chunkSize?: number;
}) {
  const [visibleCount, setVisibleCount] = useState(chunkSize);

  const schedule = window.requestIdleCallback || ((cb: Function) => setTimeout(cb, 0));
  const cancel = window.cancelIdleCallback || clearTimeout;

  useEffect(() => {
    let idleId: any = null;
    if (visibleCount < orchestrators.length) {
      idleId = schedule(() => {
        setVisibleCount((c) => Math.min(c + chunkSize, orchestrators.length));
      });
      return () => cancel(idleId);
    }
  }, [visibleCount, orchestrators.length, chunkSize]);
  return (
    <>
      {orchestrators.slice(0, visibleCount).map((orchestrator) => (
        <OrchestratorRow key={orchestrator.id} orchestrator={orchestrator} sessionContext={sessionContext} onRequery={onRequery} />
      ))}
    </>
  );
}

/**
 * ListView
 *
 * Main component for displaying a responsive, table-based list of orchestrator resources.
 * Handles loading state with skeleton rows and incremental rendering for large lists.
 *
 * @param isLoading - Whether the orchestrator data is loading (shows skeleton rows if true).
 * @param ghostRows - Number of skeleton rows to display while loading.
 * @param sessionContext - Authentication and API context for actions.
 * @param orchestrators - Array of orchestrator objects to display.
 * @param onRequery - Callback to refresh orchestrator data.
 */
export function ListView({ isLoading, ghostRows, sessionContext, objects, onRequery }: OrchestratorListViewProps) {
  console.debug(
    `${loggerPrefix} ListView() Rendering ListView - {isLoading: ${isLoading}, ghostRows: ${ghostRows}, objects length: ${Array.isArray(objects) ? objects.length : "N/A"}}`,
  );
  console.debug(`${loggerPrefix} SessionContext:`, sessionContext);
  console.debug(`${loggerPrefix} Objects:`, objects);
  return (
    <div className="table-responsive orchestrator-list-table-wrap ps-3 pe-3">
      <table className="table table-striped table-hover align-middle border">
        <TableHeader />
        <tbody>
          {isLoading ? (
            <OrchestratorRowGhosts count={ghostRows} />
          ) : (
            <ChunkedRows orchestrators={objects} sessionContext={sessionContext} onRequery={onRequery} />
          )}
        </tbody>
      </table>
    </div>
  );
}

export default ListView;

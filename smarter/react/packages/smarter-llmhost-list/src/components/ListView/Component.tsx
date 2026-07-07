/**
 * ListView
 *
 * Renders a responsive, table-based list of llmhost resources with key details and actions.
 * Features:
 * - Displays llmhost information in a styled table with columns for name, dates, llmhost, model, llmhosts, status, and actions.
 * - Integrates Toolbar for per-llmhost actions (open, edit, clone, rename, delete).
 * - Formats dates and status using shared utilities.
 * - Shows skeleton (ghost) rows while loading, and supports incremental rendering for large lists.
 *
 * Props:
 * @param isLoading - Whether the llmhost data is loading (shows skeleton rows if true).
 * @param ghostRows - Number of skeleton rows to display while loading.
 * @param sessionContext - Authentication and API context for actions.
 * @param llmhosts - Array of llmhost objects to display.
 * @param onRequery - Callback to refresh llmhost data.
 *
 * Usage:
 * <ListView
 *   sessionContext={sessionContext}
 *   llmhosts={llmhosts}
 *   isLoading={isLoading}
 *   ghostRows={ghostRows}
 *   onRequery={onRequery}
 * />
 *
 * Intended for views where llmhosts are presented in a list/table format.
 */
import React, { useState, useEffect } from "react";

import { Loading, formatDateTime } from "@smarter/common";
import type { SessionContext } from "@smarter/common";

import type { LLMHost, LLMHostListViewProps } from "@/lib/Types";
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
 * Renders the table header row for the llmhost list, including column titles for all displayed fields.
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
        <th className="d-none d-md-table-cell">Status</th>
        <th className="">Operations</th>
      </tr>
    </thead>
  );
};

/**
 * LLMHostRow
 *
 * Renders a single llmhost as a table row, displaying its details and action toolbar.
 *
 * @param llmhost - The llmhost object to display.
 * @param sessionContext - Session context for actions.
 * @param onRequery - Callback to refresh llmhost data after an action.
 */
const LLMHostRow = React.memo(function LLMHostRow({
  llmhost,
  sessionContext,
  onRequery,
}: {
  llmhost: LLMHost;
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
    <tr className="" key={llmhost.id}>
      {/* Name */}
      <td className="p-1 m-0">
        <a href={llmhost.manifestUrl}>{llmhost.name}</a>
      </td>
      {/* Created Date */}
      <td className="d-none d-lg-table-cell width-100">
        <CreatedDate date={llmhost.createdAt} />
      </td>
      {/* Updated Date */}
      <td className="d-none d-lg-table-cell width-100">
        <UpdatedDate date={llmhost.updatedAt} createdAt={llmhost.createdAt} />
      </td>
      {/* Description */}
      <td className="">{llmhost.description}</td>
      <td className="">{llmhost.isActive}</td>
      {/* Status */}
      <td className="d-none d-md-table-cell ">
        <StatusBar llmhost={llmhost} />
      </td>
      {/* Actions */}
      <td className="text-end ">
        <Toolbar sessionContext={sessionContext} llmhost={llmhost} onRequery={onRequery} />
      </td>
    </tr>
  );
});

/**
 * LLMHostRowGhost
 *
 * A skeleton row component to display while llmhost data is loading.
 * It mimics the structure of a regular LLMHostRow but with placeholder content.
 */
const LLMHostRowGhost = React.memo(function LLMHostRowGhost() {
  console.debug(`${loggerPrefix} Rendering LLMHostRowGhost`);
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
      {/* Status */}
      <td className="d-none d-md-table-cell "></td>
      {/* Actions */}
      <td className="text-end "></td>
    </tr>
  );
});

/**
 * LLMHostRowGhosts
 *
 * Renders a specified number of skeleton (ghost) rows to indicate loading state in the llmhost list.
 *
 * @param count - Number of skeleton rows to render.
 */
const LLMHostRowGhosts = React.memo(function LLMHostRowGhosts({ count }: { count: number }) {
  console.debug(`${loggerPrefix} Rendering LLMHostRowGhosts with count: ${count}`);
  return (
    <>
      {Array.from({ length: count }).map((_, idx) => (
        <LLMHostRowGhost key={idx} />
      ))}
    </>
  );
});

/**
 * ChunkedRows
 *
 * Incrementally renders llmhost rows in chunks to avoid UI blocking.
 * Uses requestIdleCallback (if available) or setTimeout as a fallback to schedule rendering.
 *
 * @param llmhosts - Array of llmhost objects to render.
 * @param sessionContext - Session context for actions.
 * @param onRequery - Callback to refresh llmhost data.
 * @param chunkSize - Number of rows to render per chunk (default: 5).
 */
function ChunkedRows({
  llmhosts,
  sessionContext,
  onRequery,
  chunkSize = 5,
}: {
  llmhosts: LLMHost[];
  sessionContext: SessionContext;
  onRequery: () => void;
  chunkSize?: number;
}) {
  const [visibleCount, setVisibleCount] = useState(chunkSize);

  const schedule = window.requestIdleCallback || ((cb: Function) => setTimeout(cb, 0));
  const cancel = window.cancelIdleCallback || clearTimeout;

  useEffect(() => {
    let idleId: any = null;
    if (visibleCount < llmhosts.length) {
      idleId = schedule(() => {
        setVisibleCount((c) => Math.min(c + chunkSize, llmhosts.length));
      });
      return () => cancel(idleId);
    }
  }, [visibleCount, llmhosts.length, chunkSize]);
  return (
    <>
      {llmhosts.slice(0, visibleCount).map((llmhost) => (
        <LLMHostRow key={llmhost.id} llmhost={llmhost} sessionContext={sessionContext} onRequery={onRequery} />
      ))}
    </>
  );
}

/**
 * ListView
 *
 * Main component for displaying a responsive, table-based list of llmhost resources.
 * Handles loading state with skeleton rows and incremental rendering for large lists.
 *
 * @param isLoading - Whether the llmhost data is loading (shows skeleton rows if true).
 * @param ghostRows - Number of skeleton rows to display while loading.
 * @param sessionContext - Authentication and API context for actions.
 * @param llmhosts - Array of llmhost objects to display.
 * @param onRequery - Callback to refresh llmhost data.
 */
export function ListView({ isLoading, ghostRows, sessionContext, objects, onRequery }: LLMHostListViewProps) {
  console.debug(
    `${loggerPrefix} ListView() Rendering ListView - {isLoading: ${isLoading}, ghostRows: ${ghostRows}, objects length: ${Array.isArray(objects) ? objects.length : "N/A"}}`,
  );
  console.debug(`${loggerPrefix} SessionContext:`, sessionContext);
  console.debug(`${loggerPrefix} Objects:`, objects);
  return (
    <div className="table-responsive llmhost-list-table-wrap ps-3 pe-3">
      <table className="table table-striped table-hover align-middle border">
        <TableHeader />
        <tbody>
          {isLoading ? (
            <LLMHostRowGhosts count={ghostRows} />
          ) : (
            <ChunkedRows llmhosts={objects} sessionContext={sessionContext} onRequery={onRequery} />
          )}
        </tbody>
      </table>
    </div>
  );
}

export default ListView;

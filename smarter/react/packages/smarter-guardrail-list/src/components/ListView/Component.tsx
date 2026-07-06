/**
 * ListView
 *
 * Renders a responsive, table-based list of guardrail resources with key details and actions.
 * Features:
 * - Displays guardrail information in a styled table with columns for name, dates, guardrail, model, guardrails, status, and actions.
 * - Integrates Toolbar for per-guardrail actions (open, edit, clone, rename, delete).
 * - Formats dates and status using shared utilities.
 * - Shows skeleton (ghost) rows while loading, and supports incremental rendering for large lists.
 *
 * Props:
 * @param isLoading - Whether the guardrail data is loading (shows skeleton rows if true).
 * @param ghostRows - Number of skeleton rows to display while loading.
 * @param sessionContext - Authentication and API context for actions.
 * @param guardrails - Array of guardrail objects to display.
 * @param onRequery - Callback to refresh guardrail data.
 *
 * Usage:
 * <ListView
 *   sessionContext={sessionContext}
 *   guardrails={guardrails}
 *   isLoading={isLoading}
 *   ghostRows={ghostRows}
 *   onRequery={onRequery}
 * />
 *
 * Intended for views where guardrails are presented in a list/table format.
 */
import React, { useState, useEffect } from "react";

import { Loading, formatDateTime } from "@smarter/common";
import type { SessionContext } from "@smarter/common";

import type { Guardrail, GuardrailListViewProps } from "@/lib/Types";
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
 * Renders the table header row for the guardrail list, including column titles for all displayed fields.
 */
const TableHeader = () => {
  return (
    <thead className="table-light border-bottom-2">
      <tr className="">
        <th className=" p-1">Name</th>
        <th className="d-none d-lg-table-cell width-100">Created</th>
        <th className="d-none d-lg-table-cell width-100">Updated</th>
        <th className="">Description</th>
        <th className="">Type</th>
        <th className="d-none d-lg-table-cell">Category</th>
        <th className="d-none d-md-table-cell">Status</th>
        <th className="">Operations</th>
      </tr>
    </thead>
  );
};

/**
 * GuardrailRow
 *
 * Renders a single guardrail as a table row, displaying its details and action toolbar.
 *
 * @param guardrail - The guardrail object to display.
 * @param sessionContext - Session context for actions.
 * @param onRequery - Callback to refresh guardrail data after an action.
 */
const GuardrailRow = React.memo(function GuardrailRow({
  guardrail,
  sessionContext,
  onRequery,
}: {
  guardrail: Guardrail;
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
    <tr className="" key={guardrail.id}>
      {/* Name */}
      <td className="p-1 m-0">
        <a href={guardrail.manifestUrl}>{guardrail.name}</a>
      </td>
      {/* Created Date */}
      <td className="d-none d-lg-table-cell width-100">
        <CreatedDate date={guardrail.createdAt} />
      </td>
      {/* Updated Date */}
      <td className="d-none d-lg-table-cell width-100">
        <UpdatedDate date={guardrail.updatedAt} createdAt={guardrail.createdAt} />
      </td>
      {/* Description */}
      <td className="">{guardrail.description}</td>
      <td className="">{guardrail.guardrailType}</td>
      <td className="">{guardrail.category}</td>
      {/* Status */}
      <td className="d-none d-md-table-cell ">
        <StatusBar guardrail={guardrail} />
      </td>
      {/* Actions */}
      <td className="text-end ">
        <Toolbar sessionContext={sessionContext} guardrail={guardrail} onRequery={onRequery} />
      </td>
    </tr>
  );
});

/**
 * GuardrailRowGhost
 *
 * A skeleton row component to display while guardrail data is loading.
 * It mimics the structure of a regular GuardrailRow but with placeholder content.
 */
const GuardrailRowGhost = React.memo(function GuardrailRowGhost() {
  console.debug(`${loggerPrefix} Rendering GuardrailRowGhost`);
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
      {/* Type */}
      <td className="d-none d-xl-table-cell"></td>
      {/* category */}
      <td className="d-none d-xl-table-cell"></td>
      {/* Status */}
      <td className="d-none d-md-table-cell "></td>
      {/* Actions */}
      <td className="text-end "></td>
    </tr>
  );
});

/**
 * GuardrailRowGhosts
 *
 * Renders a specified number of skeleton (ghost) rows to indicate loading state in the guardrail list.
 *
 * @param count - Number of skeleton rows to render.
 */
const GuardrailRowGhosts = React.memo(function GuardrailRowGhosts({ count }: { count: number }) {
  console.debug(`${loggerPrefix} Rendering GuardrailRowGhosts with count: ${count}`);
  return (
    <>
      {Array.from({ length: count }).map((_, idx) => (
        <GuardrailRowGhost key={idx} />
      ))}
    </>
  );
});

/**
 * ChunkedRows
 *
 * Incrementally renders guardrail rows in chunks to avoid UI blocking.
 * Uses requestIdleCallback (if available) or setTimeout as a fallback to schedule rendering.
 *
 * @param guardrails - Array of guardrail objects to render.
 * @param sessionContext - Session context for actions.
 * @param onRequery - Callback to refresh guardrail data.
 * @param chunkSize - Number of rows to render per chunk (default: 5).
 */
function ChunkedRows({
  guardrails,
  sessionContext,
  onRequery,
  chunkSize = 5,
}: {
  guardrails: Guardrail[];
  sessionContext: SessionContext;
  onRequery: () => void;
  chunkSize?: number;
}) {
  const [visibleCount, setVisibleCount] = useState(chunkSize);

  const schedule = window.requestIdleCallback || ((cb: Function) => setTimeout(cb, 0));
  const cancel = window.cancelIdleCallback || clearTimeout;

  useEffect(() => {
    let idleId: any = null;
    if (visibleCount < guardrails.length) {
      idleId = schedule(() => {
        setVisibleCount((c) => Math.min(c + chunkSize, guardrails.length));
      });
      return () => cancel(idleId);
    }
  }, [visibleCount, guardrails.length, chunkSize]);
  return (
    <>
      {guardrails.slice(0, visibleCount).map((guardrail) => (
        <GuardrailRow key={guardrail.id} guardrail={guardrail} sessionContext={sessionContext} onRequery={onRequery} />
      ))}
    </>
  );
}

/**
 * ListView
 *
 * Main component for displaying a responsive, table-based list of guardrail resources.
 * Handles loading state with skeleton rows and incremental rendering for large lists.
 *
 * @param isLoading - Whether the guardrail data is loading (shows skeleton rows if true).
 * @param ghostRows - Number of skeleton rows to display while loading.
 * @param sessionContext - Authentication and API context for actions.
 * @param guardrails - Array of guardrail objects to display.
 * @param onRequery - Callback to refresh guardrail data.
 */
export function ListView({ isLoading, ghostRows, sessionContext, objects, onRequery }: GuardrailListViewProps) {
  console.debug(
    `${loggerPrefix} ListView() Rendering ListView - {isLoading: ${isLoading}, ghostRows: ${ghostRows}, objects length: ${Array.isArray(objects) ? objects.length : "N/A"}}`,
  );
  console.debug(`${loggerPrefix} SessionContext:`, sessionContext);
  console.debug(`${loggerPrefix} Objects:`, objects);
  return (
    <div className="table-responsive guardrail-list-table-wrap ps-3 pe-3">
      <table className="table table-striped table-hover align-middle border">
        <TableHeader />
        <tbody>
          {isLoading ? (
            <GuardrailRowGhosts count={ghostRows} />
          ) : (
            <ChunkedRows guardrails={objects} sessionContext={sessionContext} onRequery={onRequery} />
          )}
        </tbody>
      </table>
    </div>
  );
}

export default ListView;

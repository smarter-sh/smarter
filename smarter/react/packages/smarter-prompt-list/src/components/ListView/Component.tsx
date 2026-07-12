/**
 * ListView
 *
 * Renders a responsive, table-based list of llmclient resources with key details and actions.
 * Features:
 * - Displays llmclient information in a styled table with columns for name, dates, provider, model, plugins, status, and actions.
 * - Integrates Toolbar for per-llmclient actions (open, edit, clone, rename, delete).
 * - Formats dates and status using shared utilities.
 * - Shows skeleton (ghost) rows while loading, and supports incremental rendering for large lists.
 *
 * Props:
 * @param isLoading - Whether the llmclient data is loading (shows skeleton rows if true).
 * @param ghostRows - Number of skeleton rows to display while loading.
 * @param sessionContext - Authentication and API context for actions.
 * @param llmclients - Array of llmclient objects to display.
 * @param onRequery - Callback to refresh llmclient data.
 *
 * Usage:
 * <ListView
 *   sessionContext={sessionContext}
 *   llmclients={llmclients}
 *   isLoading={isLoading}
 *   ghostRows={ghostRows}
 *   onRequery={onRequery}
 * />
 *
 * Intended for views where llmclients are presented in a list/table format.
 */
import React, { useState, useEffect } from "react";

import { Loading, LoadingText, formatDateTime } from "@smarter/common";
import type { SessionContext } from "@smarter/common";

import type { LLMClient } from "@/lib/Types";
import { Toolbar } from "@/components/Toolbar";
import { StatusBar } from "@/components/StatusBar";
import { loggerPrefix } from "@/const";

import "./styles.css";

/**
 * TableHeader
 *
 * Renders the table header row for the llmclient list, including column titles for all displayed fields.
 */
const TableHeader = () => {
  return (
    <thead className="table-light border-bottom-2">
      <tr className="">
        <th className=" p-1">Name</th>
        <th className="d-none d-lg-table-cell width-100">Created</th>
        <th className="d-none d-lg-table-cell width-100">Updated</th>
        <th className="">Description</th>
        <th className="">Provider</th>
        <th className="min-width-150">Model</th>
        <th className="d-none d-xl-table-cell">Plugins</th>
        <th className="d-none d-md-table-cell">Status</th>
        <th className="">Operations</th>
      </tr>
    </thead>
  );
};

/**
 * LLMClientRow
 *
 * Renders a single llmclient as a table row, displaying its details and action toolbar.
 *
 * @param llmclient - The llmclient object to display.
 * @param sessionContext - Session context for actions.
 * @param onRequery - Callback to refresh llmclient data after an action.
 */
const LLMClientRow = React.memo(function LLMClientRow({
  llmclient,
  sessionContext,
  onRequery,
}: {
  llmclient: LLMClient;
  sessionContext: SessionContext;
  onRequery: () => void;
}) {
  const CreatedDate = ({ date }: { date: string }) => {
    return <span>{formatDateTime(date, "date")}</span>;
  };

  const UpdatedDate = ({ date, createdAt }: { date: string; createdAt: string }) => {
    return <span>{formatDateTime(date, "relative", createdAt)}</span>;
  };

  // A helper component to display combined plugins and functions for an llmclient
  // as a comma-separated list.
  const Plugins = ({ llmclient }: { llmclient: LLMClient }) => {
    const plugins = llmclient.plugins
      ?.map((p) => p?.name || "")
      .filter(Boolean)
      .join(", ");
    const functions = llmclient.functions
      ?.map((f) => f?.name || "")
      .filter(Boolean)
      .join(", ");
    // Combine plugins and functions into a single string
    const combined = [plugins, functions].filter(Boolean).join(", ");
    return <span>{combined}</span>;
  };

  return (
    <tr className="" key={llmclient.id}>
      {/* Name */}
      <td className="p-1 m-0">
        <a href={llmclient.urlChatapp}>{llmclient.name}</a>
      </td>
      {/* Created Date */}
      <td className="d-none d-lg-table-cell width-100">
        <CreatedDate date={llmclient.createdAt} />
      </td>
      {/* Updated Date */}
      <td className="d-none d-lg-table-cell width-100">
        <UpdatedDate date={llmclient.updatedAt} createdAt={llmclient.createdAt} />
      </td>
      {/* Description */}
      <td className="">{llmclient.description}</td>
      {/* Provider */}
      <td className="">{llmclient.provider}</td>
      {/* Model */}
      <td className="min-width-150">{llmclient.defaultModel || "default"}</td>
      {/* Plugins */}
      <td className="d-none d-xl-table-cell">
        <Plugins llmclient={llmclient} />
      </td>
      {/* Status */}
      <td className="d-none d-md-table-cell ">
        <StatusBar llmclient={llmclient} />
      </td>
      {/* Actions */}
      <td className="text-end ">
        <Toolbar sessionContext={sessionContext} llmclient={llmclient} onRequery={onRequery} />
      </td>
    </tr>
  );
});

/**
 * LLMClientRowGhost
 *
 * A skeleton row component to display while llmclient data is loading.
 * It mimics the structure of a regular LLMClientRow but with placeholder content.
 */
const LLMClientRowGhost = React.memo(function LLMClientRowGhost() {
  console.debug(`${loggerPrefix} Rendering LLMClientRowGhost`);
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
      {/* Description */}
      <td className=""></td>
      {/* Provider */}
      <td className=""></td>
      {/* Model */}
      <td className="min-width-150"></td>
      {/* Plugins */}
      <td className="d-none d-xl-table-cell"></td>
      {/* Status */}
      <td className="d-none d-md-table-cell "></td>
      {/* Operations */}
      <td className="text-end "></td>
    </tr>
  );
});

/**
 * LLMClientRowGhosts
 *
 * Renders a specified number of skeleton (ghost) rows to indicate loading state in the llmclient list.
 *
 * @param count - Number of skeleton rows to render.
 */
const LLMClientRowGhosts = React.memo(function LLMClientRowGhosts({ count }: { count: number }) {
  console.debug(`${loggerPrefix} Rendering LLMClientRowGhosts with count: ${count}`);
  return (
    <>
      {Array.from({ length: count }).map((_, idx) => (
        <LLMClientRowGhost key={idx} />
      ))}
    </>
  );
});

/**
 * ChunkedRows
 *
 * Incrementally renders llmclient rows in chunks to avoid UI blocking.
 * Uses requestIdleCallback (if available) or setTimeout as a fallback to schedule rendering.
 *
 * @param llmclients - Array of llmclient objects to render.
 * @param sessionContext - Session context for actions.
 * @param onRequery - Callback to refresh llmclient data.
 * @param chunkSize - Number of rows to render per chunk (default: 5).
 */
function ChunkedRows({
  llmclients,
  sessionContext,
  onRequery,
  chunkSize = 5,
}: {
  llmclients: LLMClient[];
  sessionContext: SessionContext;
  onRequery: () => void;
  chunkSize?: number;
}) {
  const [visibleCount, setVisibleCount] = useState(chunkSize);

  const schedule = window.requestIdleCallback || ((cb: Function) => setTimeout(cb, 0));
  const cancel = window.cancelIdleCallback || clearTimeout;

  useEffect(() => {
    let idleId: any = null;
    if (visibleCount < llmclients.length) {
      idleId = schedule(() => {
        setVisibleCount((c) => Math.min(c + chunkSize, llmclients.length));
      });
      return () => cancel(idleId);
    }
  }, [visibleCount, llmclients.length, chunkSize]);
  return (
    <>
      {llmclients.slice(0, visibleCount).map((llmclient) => (
        <LLMClientRow key={llmclient.id} llmclient={llmclient} sessionContext={sessionContext} onRequery={onRequery} />
      ))}
    </>
  );
}

export interface ListViewProps {
  isLoading: boolean;
  sessionContext: SessionContext;
  objects: LLMClient[];
  onRequery: () => void;
}


/**
 * ListView
 *
 * Main component for displaying a responsive, table-based list of llmclient resources.
 * Handles loading state with skeleton rows and incremental rendering for large lists.
 *
 * @param isLoading - Whether the llmclient data is loading (shows skeleton rows if true).
 * @param sessionContext - Authentication and API context for actions.
 * @param llmclients - Array of llmclient objects to display.
 * @param onRequery - Callback to refresh llmclient data.
 */
export function ListView({ isLoading, sessionContext, objects, onRequery }: ListViewProps) {
  console.debug(
    `${loggerPrefix} ListView() Rendering ListView - {isLoading: ${isLoading}, objects length: ${Array.isArray(objects) ? objects.length : "N/A"}}`,
  );
  return (
    <div className="table-responsive prompt-list-table-wrap ps-3 pe-3">
      <table className="table table-striped table-hover align-middle border">
        <TableHeader />
        <tbody>
          {isLoading && (!objects || objects.length === 0) ? (
            <LLMClientRowGhosts count={5} />
          ) : (
            <ChunkedRows llmclients={objects} sessionContext={sessionContext} onRequery={onRequery} />
          )}
        </tbody>
      </table>
    </div>
  );
}

export default ListView;

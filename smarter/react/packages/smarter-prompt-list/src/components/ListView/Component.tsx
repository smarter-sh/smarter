/**
 * ListView
 *
 * Renders a responsive, table-based list of llm_client resources with key details and actions.
 * Features:
 * - Displays llm_client information in a styled table with columns for name, dates, provider, model, plugins, status, and actions.
 * - Integrates Toolbar for per-llm_client actions (open, edit, clone, rename, delete).
 * - Formats dates and status using shared utilities.
 * - Shows skeleton (ghost) rows while loading, and supports incremental rendering for large lists.
 *
 * Props:
 * @param isLoading - Whether the llm_client data is loading (shows skeleton rows if true).
 * @param ghostRows - Number of skeleton rows to display while loading.
 * @param sessionContext - Authentication and API context for actions.
 * @param llm_clients - Array of llm_client objects to display.
 * @param onRequery - Callback to refresh llm_client data.
 *
 * Usage:
 * <ListView
 *   sessionContext={sessionContext}
 *   llm_clients={llm_clients}
 *   isLoading={isLoading}
 *   ghostRows={ghostRows}
 *   onRequery={onRequery}
 * />
 *
 * Intended for views where llm_clients are presented in a list/table format.
 */
import React, { useState, useEffect } from "react";

import type { LLMClient, SessionContext } from "@/lib/Types";
import { formatDateTime } from "@/lib/formatDateTime";
import { Toolbar } from "@/components/Toolbar";
import { StatusBar } from "@/components/StatusBar";
import { loggerPrefix } from "@/const";
import Loading from "@/components/Loading";

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
 * Renders the table header row for the llm_client list, including column titles for all displayed fields.
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
 * Renders a single llm_client as a table row, displaying its details and action toolbar.
 *
 * @param llm_client - The llm_client object to display.
 * @param sessionContext - Session context for actions.
 * @param onRequery - Callback to refresh llm_client data after an action.
 */
const LLMClientRow = React.memo(function LLMClientRow({
  llm_client,
  sessionContext,
  onRequery,
}: {
  llm_client: LLMClient;
  sessionContext: SessionContext;
  onRequery: () => void;
}) {
  const CreatedDate = ({ date }: { date: string }) => {
    return <span>{formatDateTime(date, "date")}</span>;
  };

  const UpdatedDate = ({ date, createdAt }: { date: string; createdAt: string }) => {
    return <span>{formatDateTime(date, "relative", createdAt)}</span>;
  };

  // A helper component to display combined plugins and functions for a llm_client
  // as a comma-separated list.
  const Plugins = ({ llm_client }: { llm_client: LLMClient }) => {
    const plugins = llm_client.plugins
      ?.map((p) => p?.name || "")
      .filter(Boolean)
      .join(", ");
    const functions = llm_client.functions
      ?.map((f) => f?.name || "")
      .filter(Boolean)
      .join(", ");
    // Combine plugins and functions into a single string
    const combined = [plugins, functions].filter(Boolean).join(", ");
    return <span>{combined}</span>;
  };

  return (
    <tr className="" key={llm_client.id}>
      {/* Name */}
      <td className="p-1 m-0">
        <a href={llm_client.urlChatapp}>{llm_client.name}</a>
      </td>
      {/* Created Date */}
      <td className="d-none d-lg-table-cell width-100">
        <CreatedDate date={llm_client.createdAt} />
      </td>
      {/* Updated Date */}
      <td className="d-none d-lg-table-cell width-100">
        <UpdatedDate date={llm_client.updatedAt} createdAt={llm_client.createdAt} />
      </td>
      {/* Description */}
      <td className="">{llm_client.description}</td>
      {/* Provider */}
      <td className="">{llm_client.provider}</td>
      {/* Model */}
      <td className="min-width-150">{llm_client.defaultModel || "default"}</td>
      {/* Plugins */}
      <td className="d-none d-xl-table-cell">
        <Plugins llm_client={llm_client} />
      </td>
      {/* Status */}
      <td className="d-none d-md-table-cell ">
        <StatusBar llm_client={llm_client} />
      </td>
      {/* Actions */}
      <td className="text-end ">
        <Toolbar sessionContext={sessionContext} llm_client={llm_client} onRequery={onRequery} />
      </td>
    </tr>
  );
});

/**
 * LLMClientRowGhost
 *
 * A skeleton row component to display while llm_client data is loading.
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
 * Renders a specified number of skeleton (ghost) rows to indicate loading state in the llm_client list.
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
 * Incrementally renders llm_client rows in chunks to avoid UI blocking.
 * Uses requestIdleCallback (if available) or setTimeout as a fallback to schedule rendering.
 *
 * @param llm_clients - Array of llm_client objects to render.
 * @param sessionContext - Session context for actions.
 * @param onRequery - Callback to refresh llm_client data.
 * @param chunkSize - Number of rows to render per chunk (default: 5).
 */
function ChunkedRows({
  llm_clients,
  sessionContext,
  onRequery,
  chunkSize = 5,
}: {
  llm_clients: LLMClient[];
  sessionContext: SessionContext;
  onRequery: () => void;
  chunkSize?: number;
}) {
  const [visibleCount, setVisibleCount] = useState(chunkSize);

  const schedule = window.requestIdleCallback || ((cb: Function) => setTimeout(cb, 0));
  const cancel = window.cancelIdleCallback || clearTimeout;

  useEffect(() => {
    let idleId: any = null;
    if (visibleCount < llm_clients.length) {
      idleId = schedule(() => {
        setVisibleCount((c) => Math.min(c + chunkSize, llm_clients.length));
      });
      return () => cancel(idleId);
    }
  }, [visibleCount, llm_clients.length, chunkSize]);
  return (
    <>
      {llm_clients.slice(0, visibleCount).map((llm_client) => (
        <LLMClientRow key={llm_client.id} llm_client={llm_client} sessionContext={sessionContext} onRequery={onRequery} />
      ))}
    </>
  );
}

interface ListViewProps {
  isLoading: boolean;
  ghostRows: number;
  sessionContext: SessionContext;
  objects: LLMClient[];
  onRequery: () => void;
}


/**
 * ListView
 *
 * Main component for displaying a responsive, table-based list of llm_client resources.
 * Handles loading state with skeleton rows and incremental rendering for large lists.
 *
 * @param isLoading - Whether the llm_client data is loading (shows skeleton rows if true).
 * @param ghostRows - Number of skeleton rows to display while loading.
 * @param sessionContext - Authentication and API context for actions.
 * @param llm_clients - Array of llm_client objects to display.
 * @param onRequery - Callback to refresh llm_client data.
 */
export function ListView({ isLoading, ghostRows, sessionContext, objects, onRequery }: ListViewProps) {
  console.debug(
    `${loggerPrefix} Rendering ListView - {isLoading: ${isLoading}, ghostRows: ${ghostRows}, objects length: ${Array.isArray(objects) ? objects.length : "N/A"}}`,
  );
  return (
    <div className="table-responsive prompt-list-table-wrap ps-3 pe-3">
      <table className="table table-striped table-hover align-middle border">
        <TableHeader />
        <tbody>
          {isLoading && (!objects || objects.length === 0) ? (
            <LLMClientRowGhosts count={ghostRows} />
          ) : (
            <ChunkedRows llm_clients={objects} sessionContext={sessionContext} onRequery={onRequery} />
          )}
        </tbody>
      </table>
    </div>
  );
}

export default ListView;

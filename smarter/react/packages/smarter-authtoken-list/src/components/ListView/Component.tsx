/**
 * ListView
 *
 * Renders a responsive, table-based list of authtoken resources with key details and actions.
 * Features:
 * - Displays authtoken information in a styled table with columns for name, dates, provider, model, authtokens, status, and actions.
 * - Integrates Toolbar for per-authtoken actions (open, edit, clone, rename, delete).
 * - Formats dates and status using shared utilities.
 * - Shows skeleton (ghost) rows while loading, and supports incremental rendering for large lists.
 *
 * Props:
 * @param isLoading - Whether the authtoken data is loading (shows skeleton rows if true).
 * @param ghostRows - Number of skeleton rows to display while loading.
 * @param sessionContext - Authentication and API context for actions.
 * @param authtokens - Array of authtoken objects to display.
 * @param onRequery - Callback to refresh authtoken data.
 *
 * Usage:
 * <ListView
 *   sessionContext={sessionContext}
 *   authtokens={authtokens}
 *   isLoading={isLoading}
 *   ghostRows={ghostRows}
 *   onRequery={onRequery}
 * />
 *
 * Intended for views where authtokens are presented in a list/table format.
 */
import React, { useState, useEffect } from "react";

import { Loading } from "@smarter/common";
import type { SessionContext } from "@smarter/common";

import type { AuthToken, AuthTokenListViewProps } from "@/lib/Types";
import { formatDateTime } from "@smarter/common";
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
 * Renders the table header row for the authtoken list, including column titles for all displayed fields.
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
 * AuthTokenRow
 *
 * Renders a single authtoken as a table row, displaying its details and action toolbar.
 *
 * @param authtoken - The authtoken object to display.
 * @param sessionContext - Session context for actions.
 * @param onRequery - Callback to refresh authtoken data after an action.
 */
const AuthTokenRow = React.memo(function AuthTokenRow({
  authtoken,
  sessionContext,
  onRequery,
}: {
  authtoken: AuthToken;
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
    <tr className="" key={authtoken.id}>
      {/* Name */}
      <td className="p-1 m-0">
        <a href={authtoken.manifestUrl}>{authtoken.name}</a>
      </td>
      {/* Created Date */}
      <td className="d-none d-lg-table-cell width-100">
        <CreatedDate date={authtoken.createdAt} />
      </td>
      {/* Updated Date */}
      <td className="d-none d-lg-table-cell width-100">
        <UpdatedDate date={authtoken.updatedAt} createdAt={authtoken.createdAt} />
      </td>
      {/* Description */}
      <td className="">{authtoken.description}</td>
      {/* Status */}
      <td className="d-none d-md-table-cell ">
        <StatusBar authtoken={authtoken} />
      </td>
      {/* Actions */}
      <td className="text-end ">
        <Toolbar sessionContext={sessionContext} authtoken={authtoken} onRequery={onRequery} />
      </td>
    </tr>
  );
});

/**
 * AuthTokenRowGhost
 *
 * A skeleton row component to display while authtoken data is loading.
 * It mimics the structure of a regular AuthTokenRow but with placeholder content.
 */
const AuthTokenRowGhost = React.memo(function AuthTokenRowGhost() {
  console.debug(`${loggerPrefix} Rendering AuthTokenRowGhost`);
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
 * AuthTokenRowGhosts
 *
 * Renders a specified number of skeleton (ghost) rows to indicate loading state in the authtoken list.
 *
 * @param count - Number of skeleton rows to render.
 */
const AuthTokenRowGhosts = React.memo(function AuthTokenRowGhosts({ count }: { count: number }) {
  console.debug(`${loggerPrefix} Rendering AuthTokenRowGhosts with count: ${count}`);
  return (
    <>
      {Array.from({ length: count }).map((_, idx) => (
        <AuthTokenRowGhost key={idx} />
      ))}
    </>
  );
});

/**
 * ChunkedRows
 *
 * Incrementally renders authtoken rows in chunks to avoid UI blocking.
 * Uses requestIdleCallback (if available) or setTimeout as a fallback to schedule rendering.
 *
 * @param authtokens - Array of authtoken objects to render.
 * @param sessionContext - Session context for actions.
 * @param onRequery - Callback to refresh authtoken data.
 * @param chunkSize - Number of rows to render per chunk (default: 5).
 */
function ChunkedRows({
  authtokens,
  sessionContext,
  onRequery,
  chunkSize = 5,
}: {
  authtokens: AuthToken[];
  sessionContext: SessionContext;
  onRequery: () => void;
  chunkSize?: number;
}) {
  const [visibleCount, setVisibleCount] = useState(chunkSize);

  const schedule = window.requestIdleCallback || ((cb: Function) => setTimeout(cb, 0));
  const cancel = window.cancelIdleCallback || clearTimeout;

  useEffect(() => {
    let idleId: any = null;
    if (visibleCount < authtokens.length) {
      idleId = schedule(() => {
        setVisibleCount((c) => Math.min(c + chunkSize, authtokens.length));
      });
      return () => cancel(idleId);
    }
  }, [visibleCount, authtokens.length, chunkSize]);
  return (
    <>
      {authtokens.slice(0, visibleCount).map((authtoken) => (
        <AuthTokenRow key={authtoken.id} authtoken={authtoken} sessionContext={sessionContext} onRequery={onRequery} />
      ))}
    </>
  );
}

/**
 * ListView
 *
 * Main component for displaying a responsive, table-based list of authtoken resources.
 * Handles loading state with skeleton rows and incremental rendering for large lists.
 *
 * @param isLoading - Whether the authtoken data is loading (shows skeleton rows if true).
 * @param ghostRows - Number of skeleton rows to display while loading.
 * @param sessionContext - Authentication and API context for actions.
 * @param authtokens - Array of authtoken objects to display.
 * @param onRequery - Callback to refresh authtoken data.
 */
export function ListView({ isLoading, ghostRows, sessionContext, objects, onRequery }: AuthTokenListViewProps) {
  console.debug(
    `${loggerPrefix} Rendering ListView - {isLoading: ${isLoading}, ghostRows: ${ghostRows}, objects length: ${Array.isArray(objects) ? objects.length : "N/A"}}`,
  );
  return (
    <div className="table-responsive authtoken-list-table-wrap ps-3 pe-3">
      <table className="table table-striped table-hover align-middle border">
        <TableHeader />
        <tbody>
          {isLoading ? (
            <AuthTokenRowGhosts count={ghostRows} />
          ) : (
            <ChunkedRows authtokens={objects} sessionContext={sessionContext} onRequery={onRequery} />
          )}
        </tbody>
      </table>
    </div>
  );
}

export default ListView;

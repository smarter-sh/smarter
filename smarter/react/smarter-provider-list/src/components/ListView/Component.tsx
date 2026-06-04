/**
 * ListView
 *
 * Renders a responsive, table-based list of provider resources with key details and actions.
 * Features:
 * - Displays provider information in a styled table with columns for name, dates, provider, model, providers, status, and actions.
 * - Integrates Toolbar for per-provider actions (open, edit, clone, rename, delete).
 * - Formats dates and status using shared utilities.
 * - Shows skeleton (ghost) rows while loading, and supports incremental rendering for large lists.
 *
 * Props:
 * @param isLoading - Whether the provider data is loading (shows skeleton rows if true).
 * @param ghostRows - Number of skeleton rows to display while loading.
 * @param sessionContext - Authentication and API context for actions.
 * @param providers - Array of provider objects to display.
 * @param onRequery - Callback to refresh provider data.
 *
 * Usage:
 * <ListView
 *   sessionContext={sessionContext}
 *   providers={providers}
 *   isLoading={isLoading}
 *   ghostRows={ghostRows}
 *   onRequery={onRequery}
 * />
 *
 * Intended for views where providers are presented in a list/table format.
 */
import React, { useState, useEffect } from "react";

import { Loading } from "@smarter/common";
import type { SessionContext } from "@smarter/common";

import type { Provider, ProviderListViewProps } from "@/lib/Types";
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
 * Renders the table header row for the provider list, including column titles for all displayed fields.
 */
const TableHeader = () => {
  return (
    <thead className="table-light border-bottom-2">
      <tr className="">
        <th className=" p-1">Name</th>
        <th className="d-none d-lg-table-cell width-100">Created</th>
        <th className="d-none d-lg-table-cell width-100">Updated</th>
        <th className="">Description</th>
        <th className="">API Key</th>
        <th className="d-none d-md-table-cell">Status</th>
        <th className="">Operations</th>
      </tr>
    </thead>
  );
};

/**
 * ProviderRow
 *
 * Renders a single provider as a table row, displaying its details and action toolbar.
 *
 * @param provider - The provider object to display.
 * @param sessionContext - Session context for actions.
 * @param onRequery - Callback to refresh provider data after an action.
 */
const ProviderRow = React.memo(function ProviderRow({
  provider,
  sessionContext,
  onRequery,
}: {
  provider: Provider;
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
    <tr className="" key={provider.id}>
      {/* Name */}
      <td className="p-1 m-0">
        <a href={provider.manifestUrl}>{provider.name}</a>
      </td>
      {/* Created Date */}
      <td className="d-none d-lg-table-cell width-100">
        <CreatedDate date={provider.createdAt} />
      </td>
      {/* Updated Date */}
      <td className="d-none d-lg-table-cell width-100">
        <UpdatedDate date={provider.updatedAt} createdAt={provider.createdAt} />
      </td>
      {/* Description */}
      <td className="">{provider.description}</td>
      {/* API Key */}
      <td className=""><a href={provider.apiKey.manifestUrl}>{provider.apiKey.name}</a></td>
      {/* Status */}
      <td className="d-none d-md-table-cell ">
        <StatusBar provider={provider} />
      </td>
      {/* Actions */}
      <td className="text-end ">
        <Toolbar sessionContext={sessionContext} provider={provider} onRequery={onRequery} />
      </td>
    </tr>
  );
});

/**
 * ProviderRowGhost
 *
 * A skeleton row component to display while provider data is loading.
 * It mimics the structure of a regular ProviderRow but with placeholder content.
 */
const ProviderRowGhost = React.memo(function ProviderRowGhost() {
  console.debug(`${loggerPrefix} Rendering ProviderRowGhost`);
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
 * ProviderRowGhosts
 *
 * Renders a specified number of skeleton (ghost) rows to indicate loading state in the provider list.
 *
 * @param count - Number of skeleton rows to render.
 */
const ProviderRowGhosts = React.memo(function ProviderRowGhosts({ count }: { count: number }) {
  console.debug(`${loggerPrefix} Rendering ProviderRowGhosts with count: ${count}`);
  return (
    <>
      {Array.from({ length: count }).map((_, idx) => (
        <ProviderRowGhost key={idx} />
      ))}
    </>
  );
});

/**
 * ChunkedRows
 *
 * Incrementally renders provider rows in chunks to avoid UI blocking.
 * Uses requestIdleCallback (if available) or setTimeout as a fallback to schedule rendering.
 *
 * @param providers - Array of provider objects to render.
 * @param sessionContext - Session context for actions.
 * @param onRequery - Callback to refresh provider data.
 * @param chunkSize - Number of rows to render per chunk (default: 5).
 */
function ChunkedRows({
  providers,
  sessionContext,
  onRequery,
  chunkSize = 5,
}: {
  providers: Provider[];
  sessionContext: SessionContext;
  onRequery: () => void;
  chunkSize?: number;
}) {
  const [visibleCount, setVisibleCount] = useState(chunkSize);

  const schedule = window.requestIdleCallback || ((cb: Function) => setTimeout(cb, 0));
  const cancel = window.cancelIdleCallback || clearTimeout;

  useEffect(() => {
    let idleId: any = null;
    if (visibleCount < providers.length) {
      idleId = schedule(() => {
        setVisibleCount((c) => Math.min(c + chunkSize, providers.length));
      });
      return () => cancel(idleId);
    }
  }, [visibleCount, providers.length, chunkSize]);
  return (
    <>
      {providers.slice(0, visibleCount).map((provider) => (
        <ProviderRow key={provider.id} provider={provider} sessionContext={sessionContext} onRequery={onRequery} />
      ))}
    </>
  );
}

/**
 * ListView
 *
 * Main component for displaying a responsive, table-based list of provider resources.
 * Handles loading state with skeleton rows and incremental rendering for large lists.
 *
 * @param isLoading - Whether the provider data is loading (shows skeleton rows if true).
 * @param ghostRows - Number of skeleton rows to display while loading.
 * @param sessionContext - Authentication and API context for actions.
 * @param providers - Array of provider objects to display.
 * @param onRequery - Callback to refresh provider data.
 */
export function ListView({ isLoading, ghostRows, sessionContext, objects, onRequery }: ProviderListViewProps) {
  console.debug(
    `${loggerPrefix} Rendering ListView - {isLoading: ${isLoading}, ghostRows: ${ghostRows}, objects length: ${Array.isArray(objects) ? objects.length : "N/A"}}`,
  );
  console.debug(`${loggerPrefix} SessionContext:`, sessionContext);
  console.debug(`${loggerPrefix} Objects:`, objects);
  return (
    <div className="table-responsive provider-list-table-wrap ps-3 pe-3">
      <table className="table table-striped table-hover align-middle border">
        <TableHeader />
        <tbody>
          {isLoading ? (
            <ProviderRowGhosts count={ghostRows} />
          ) : (
            <ChunkedRows providers={objects} sessionContext={sessionContext} onRequery={onRequery} />
          )}
        </tbody>
      </table>
    </div>
  );
}

export default ListView;

/**
 * ListView
 *
 * Renders a responsive, table-based list of proxy resources with key details and actions.
 * Features:
 * - Displays proxy information in a styled table with columns for name, provider, the provider's API host,
 *   the API key's Secret, status, and actions.
 * - Integrates Toolbar for per-proxy actions (copy URL, edit, clone, rename, delete).
 * - Shows skeleton (ghost) rows while loading, and supports incremental rendering for large lists.
 *
 * Props:
 * @param isLoading - Whether the proxy data is loading (shows skeleton rows if true).
 * @param ghostRows - Number of skeleton rows to display while loading.
 * @param sessionContext - Authentication and API context for actions.
 * @param objects - Array of proxy objects to display.
 * @param onRequery - Callback to refresh proxy data.
 *
 * Usage:
 * <ListView
 *   sessionContext={sessionContext}
 *   objects={proxies}
 *   isLoading={isLoading}
 *   ghostRows={ghostRows}
 *   onRequery={onRequery}
 * />
 *
 * Intended for views where proxies are presented in a list/table format.
 */
import React, { useState, useEffect } from "react";

import { Loading, SortableHeader } from "@smarter/common";
import type { SessionContext, Sorting } from "@smarter/common";

import type { Proxy, ProxyListViewProps } from "@/lib/Types";
import { Toolbar } from "@/components/Toolbar";
import { StatusBar } from "@/components/StatusBar";
import { loggerPrefix } from "@/lib/const";
import { formatApiKey, upstreamHost } from "@/lib/format";

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
 * Renders the table header row for the proxy list, including column titles for all displayed fields.
 * Its sortable columns sort the list, with the list api (see SortableHeader).
 */
const TableHeader = ({ sorting }: { sorting?: Sorting }) => {
  return (
    <thead className="table-light border-bottom-2">
      <tr className="">
        <SortableHeader column="name" sorting={sorting} className=" p-1">
          Name
        </SortableHeader>
        <SortableHeader column="providerName" sorting={sorting} className="">
          Provider
        </SortableHeader>
        <th className="d-none d-lg-table-cell">Provider API</th>
        <th className="d-none d-lg-table-cell">API Key</th>
        <th className="d-none d-md-table-cell">Status</th>
        <th className="">Operations</th>
      </tr>
    </thead>
  );
};

/**
 * ProxyRow
 *
 * Renders a single proxy as a table row, displaying its details and action toolbar.
 *
 * @param proxy - The proxy object to display.
 * @param sessionContext - Session context for actions.
 * @param onRequery - Callback to refresh proxy data after an action.
 */
const ProxyRow = React.memo(function ProxyRow({
  proxy,
  sessionContext,
  onRequery,
}: {
  proxy: Proxy;
  sessionContext: SessionContext;
  onRequery: () => void;
}) {
  return (
    <tr className="" key={proxy.id}>
      {/* Name */}
      <td className="p-1 m-0">
        <a href={proxy.manifestUrl} title={proxy.description}>
          {proxy.name}
        </a>
      </td>
      {/* Provider */}
      <td className="">{proxy.providerName}</td>
      {/* Provider API */}
      <td className="d-none d-lg-table-cell" title={proxy.upstreamUrl}>
        {upstreamHost(proxy)}
      </td>
      {/* API Key */}
      <td className="d-none d-lg-table-cell">{formatApiKey(proxy)}</td>
      {/* Status */}
      <td className="d-none d-md-table-cell ">
        <StatusBar proxy={proxy} />
      </td>
      {/* Actions */}
      <td className="text-end ">
        <Toolbar sessionContext={sessionContext} proxy={proxy} onRequery={onRequery} />
      </td>
    </tr>
  );
});

/**
 * ProxyRowGhost
 *
 * A skeleton row component to display while proxy data is loading.
 * It has the same columns as ProxyRow, with placeholder content.
 */
const ProxyRowGhost = React.memo(function ProxyRowGhost() {
  console.debug(`${loggerPrefix} Rendering ProxyRowGhost`);
  return (
    <tr className="ghost">
      {/* Name */}
      <td className="p-1 m-0">
        <Loading />
      </td>
      {/* Provider */}
      <td className="">
        <LoadingText />
      </td>
      {/* Provider API */}
      <td className="d-none d-lg-table-cell"></td>
      {/* API Key */}
      <td className="d-none d-lg-table-cell"></td>
      {/* Status */}
      <td className="d-none d-md-table-cell "></td>
      {/* Actions */}
      <td className="text-end "></td>
    </tr>
  );
});

/**
 * ProxyRowGhosts
 *
 * Renders a specified number of skeleton (ghost) rows to indicate loading state in the proxy list.
 *
 * @param count - Number of skeleton rows to render.
 */
const ProxyRowGhosts = React.memo(function ProxyRowGhosts({ count }: { count: number }) {
  console.debug(`${loggerPrefix} Rendering ProxyRowGhosts with count: ${count}`);
  return (
    <>
      {Array.from({ length: count }).map((_, idx) => (
        <ProxyRowGhost key={idx} />
      ))}
    </>
  );
});

/**
 * ChunkedRows
 *
 * Incrementally renders proxy rows in chunks to avoid UI blocking.
 * Uses requestIdleCallback (if available) or setTimeout as a fallback to schedule rendering.
 *
 * @param proxies - Array of proxy objects to render.
 * @param sessionContext - Session context for actions.
 * @param onRequery - Callback to refresh proxy data.
 * @param chunkSize - Number of rows to render per chunk (default: 5).
 */
function ChunkedRows({
  proxies,
  sessionContext,
  onRequery,
  chunkSize = 5,
}: {
  proxies: Proxy[];
  sessionContext: SessionContext;
  onRequery: () => void;
  chunkSize?: number;
}) {
  const [visibleCount, setVisibleCount] = useState(chunkSize);

  useEffect(() => {
    if (visibleCount >= proxies.length) return;
    const next = () => setVisibleCount((c) => Math.min(c + chunkSize, proxies.length));
    if (window.requestIdleCallback) {
      const idleId = window.requestIdleCallback(next);
      return () => window.cancelIdleCallback(idleId);
    }
    const timeoutId = setTimeout(next, 0);
    return () => clearTimeout(timeoutId);
  }, [visibleCount, proxies.length, chunkSize]);
  return (
    <>
      {proxies.slice(0, visibleCount).map((proxy) => (
        <ProxyRow key={proxy.id} proxy={proxy} sessionContext={sessionContext} onRequery={onRequery} />
      ))}
    </>
  );
}

/**
 * ListView
 *
 * Main component for displaying a responsive, table-based list of proxy resources.
 * Handles loading state with skeleton rows and incremental rendering for large lists.
 *
 * @param isLoading - Whether the proxy data is loading (shows skeleton rows if true).
 * @param ghostRows - Number of skeleton rows to display while loading.
 * @param sessionContext - Authentication and API context for actions.
 * @param objects - Array of proxy objects to display.
 * @param onRequery - Callback to refresh proxy data.
 * @param sorting - The sort of the list, which its sortable column headers change.
 */
export function ListView({ isLoading, ghostRows, sessionContext, objects, onRequery, sorting }: ProxyListViewProps) {
  console.debug(
    `${loggerPrefix} ListView() Rendering ListView - {isLoading: ${isLoading}, ghostRows: ${ghostRows}, objects length: ${Array.isArray(objects) ? objects.length : "N/A"}}`,
  );
  return (
    <div className="table-responsive proxy-list-table-wrap ps-3 pe-3">
      <table className="table table-striped table-hover align-middle border">
        <TableHeader sorting={sorting} />
        <tbody>
          {isLoading ? (
            <ProxyRowGhosts count={ghostRows} />
          ) : (
            <ChunkedRows proxies={objects} sessionContext={sessionContext} onRequery={onRequery} />
          )}
        </tbody>
      </table>
    </div>
  );
}

export default ListView;

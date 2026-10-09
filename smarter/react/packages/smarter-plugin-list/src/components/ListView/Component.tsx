/**
 * ListView
 *
 * Renders a responsive, table-based list of plugin resources with key details and actions.
 * Features:
 * - Displays plugin information in a styled table with columns for name, dates, provider, model, plugins, status, and actions.
 * - Integrates Toolbar for per-plugin actions (open, edit, clone, rename, delete).
 * - Formats dates and status using shared utilities.
 * - Shows skeleton (ghost) rows while loading, and supports incremental rendering for large lists.
 *
 * Props:
 * @param isLoading - Whether the plugin data is loading (shows skeleton rows if true).
 * @param ghostRows - Number of skeleton rows to display while loading.
 * @param sessionContext - Authentication and API context for actions.
 * @param plugins - Array of plugin objects to display.
 * @param onRequery - Callback to refresh plugin data.
 *
 * Usage:
 * <ListView
 *   sessionContext={sessionContext}
 *   plugins={plugins}
 *   isLoading={isLoading}
 *   ghostRows={ghostRows}
 *   onRequery={onRequery}
 * />
 *
 * Intended for views where plugins are presented in a list/table format.
 */
import React, { useState, useEffect } from "react";

import { formatDateTime, Loading, SortableHeader } from "@smarter/common";
import type { SessionContext, Sorting } from "@smarter/common";

import type { Plugin, PluginListViewProps } from "@/lib/Types";
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
 * Renders the table header row for the plugin list, including column titles for all displayed fields.
 * Its sortable columns sort the list, with the list api (see SortableHeader).
 */
const TableHeader = ({ sorting }: { sorting?: Sorting }) => {
  return (
    <thead className="table-light border-bottom-2">
      <tr className="">
        <SortableHeader column="name" sorting={sorting} className=" p-1">
          Name
        </SortableHeader>
        <SortableHeader column="createdAt" sorting={sorting} className="d-none d-lg-table-cell width-100">
          Created
        </SortableHeader>
        <SortableHeader column="updatedAt" sorting={sorting} className="d-none d-lg-table-cell width-100">
          Updated
        </SortableHeader>
        <SortableHeader column="kind" sorting={sorting} className="">
          Kind
        </SortableHeader>
        <SortableHeader column="description" sorting={sorting} className="">
          Description
        </SortableHeader>
        <SortableHeader column="selector" sorting={sorting} className="min-width-150">
          Selector
        </SortableHeader>
        <th className="d-none d-md-table-cell">Status</th>
        <th className="">Operations</th>
      </tr>
    </thead>
  );
};

/**
 * CreatedDate and UpdatedDate
 *
 * Format a row's creation date, and its last update relative to its creation.
 */
const CreatedDate = ({ date }: { date: string }) => {
  return <span>{formatDateTime(date, "date")}</span>;
};

const UpdatedDate = ({ date, createdAt }: { date: string; createdAt: string }) => {
  return <span>{formatDateTime(date, "relative", createdAt)}</span>;
};

/**
 * PluginRow
 *
 * Renders a single plugin as a table row, displaying its details and action toolbar.
 *
 * @param plugin - The plugin object to display.
 * @param sessionContext - Session context for actions.
 * @param onRequery - Callback to refresh plugin data after an action.
 */
const PluginRow = React.memo(function PluginRow({
  plugin,
  sessionContext,
  onRequery,
}: {
  plugin: Plugin;
  sessionContext: SessionContext;
  onRequery: () => void;
}) {
  return (
    <tr className="" key={plugin.id}>
      {/* Name */}
      <td className="p-1 m-0">
        <a href={plugin.manifestUrl}>{plugin.name}</a>
      </td>
      {/* Created Date */}
      <td className="d-none d-lg-table-cell width-100">
        <CreatedDate date={plugin.createdAt} />
      </td>
      {/* Updated Date */}
      <td className="d-none d-lg-table-cell width-100">
        <UpdatedDate date={plugin.updatedAt} createdAt={plugin.createdAt} />
      </td>
      {/* Kind */}
      <td className="">{plugin.kind}</td>
      {/* Description */}
      <td className="">{plugin.description}</td>
      {/* Selector */}
      <td className="min-width-150">{plugin.selector.directive}</td>
      {/* Status */}
      <td className="d-none d-md-table-cell ">
        <StatusBar plugin={plugin} />
      </td>
      {/* Actions */}
      <td className="text-end ">
        <Toolbar sessionContext={sessionContext} plugin={plugin} onRequery={onRequery} />
      </td>
    </tr>
  );
});

/**
 * PluginRowGhost
 *
 * A skeleton row component to display while plugin data is loading.
 * It mimics the structure of a regular PluginRow but with placeholder content.
 */
const PluginRowGhost = React.memo(function PluginRowGhost() {
  console.debug(`${loggerPrefix} Rendering PluginRowGhost`);
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
 * PluginRowGhosts
 *
 * Renders a specified number of skeleton (ghost) rows to indicate loading state in the plugin list.
 *
 * @param count - Number of skeleton rows to render.
 */
const PluginRowGhosts = React.memo(function PluginRowGhosts({ count }: { count: number }) {
  console.debug(`${loggerPrefix} Rendering PluginRowGhosts with count: ${count}`);
  return (
    <>
      {Array.from({ length: count }).map((_, idx) => (
        <PluginRowGhost key={idx} />
      ))}
    </>
  );
});

/**
 * ChunkedRows
 *
 * Incrementally renders plugin rows in chunks to avoid UI blocking.
 * Uses requestIdleCallback (if available) or setTimeout as a fallback to schedule rendering.
 *
 * @param plugins - Array of plugin objects to render.
 * @param sessionContext - Session context for actions.
 * @param onRequery - Callback to refresh plugin data.
 * @param chunkSize - Number of rows to render per chunk (default: 5).
 */
function ChunkedRows({
  plugins,
  sessionContext,
  onRequery,
  chunkSize = 5,
}: {
  plugins: Plugin[];
  sessionContext: SessionContext;
  onRequery: () => void;
  chunkSize?: number;
}) {
  const [visibleCount, setVisibleCount] = useState(chunkSize);

  useEffect(() => {
    if (visibleCount >= plugins.length) return;
    const next = () => setVisibleCount((c) => Math.min(c + chunkSize, plugins.length));
    if (window.requestIdleCallback) {
      const idleId = window.requestIdleCallback(next);
      return () => window.cancelIdleCallback(idleId);
    }
    const timeoutId = setTimeout(next, 0);
    return () => clearTimeout(timeoutId);
  }, [visibleCount, plugins.length, chunkSize]);
  return (
    <>
      {plugins.slice(0, visibleCount).map((plugin) => (
        <PluginRow key={plugin.id} plugin={plugin} sessionContext={sessionContext} onRequery={onRequery} />
      ))}
    </>
  );
}

/**
 * ListView
 *
 * Main component for displaying a responsive, table-based list of plugin resources.
 * Handles loading state with skeleton rows and incremental rendering for large lists.
 *
 * @param isLoading - Whether the plugin data is loading (shows skeleton rows if true).
 * @param ghostRows - Number of skeleton rows to display while loading.
 * @param sessionContext - Authentication and API context for actions.
 * @param plugins - Array of plugin objects to display.
 * @param onRequery - Callback to refresh plugin data.
 * @param sorting - The sort of the list, which its sortable column headers change.
 */
export function ListView({ isLoading, ghostRows, sessionContext, objects, onRequery, sorting }: PluginListViewProps) {
  console.debug(
    `${loggerPrefix} ListView() Rendering ListView - {isLoading: ${isLoading}, ghostRows: ${ghostRows}, objects length: ${Array.isArray(objects) ? objects.length : "N/A"}}`,
  );
  return (
    <div className="table-responsive plugin-list-table-wrap ps-3 pe-3">
      <table className="table table-striped table-hover align-middle border">
        <TableHeader sorting={sorting} />
        <tbody>
          {isLoading ? (
            <PluginRowGhosts count={ghostRows} />
          ) : (
            <ChunkedRows plugins={objects} sessionContext={sessionContext} onRequery={onRequery} />
          )}
        </tbody>
      </table>
    </div>
  );
}

export default ListView;

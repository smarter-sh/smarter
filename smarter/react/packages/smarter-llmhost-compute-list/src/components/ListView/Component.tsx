/**
 * ListView
 *
 * Renders a responsive, table-based list of LLMHostCompute resources with key details and actions.
 * Features:
 * - Displays each LLMHostCompute's kind of node (instance type, GPUs, CPU and memory, price) and its
 *   node group's status in a styled table.
 * - Integrates Toolbar for per-LLMHostCompute actions (manifest, clone, rename, delete).
 * - Shows skeleton (ghost) rows while loading, and supports incremental rendering for large lists.
 *
 * Props:
 * @param isLoading - Whether the data is loading (shows skeleton rows if true).
 * @param ghostRows - Number of skeleton rows to display while loading.
 * @param sessionContext - Authentication and API context for actions.
 * @param objects - Array of LLMHostCompute objects to display.
 * @param onRequery - Callback to refresh the data.
 *
 * Usage:
 * <ListView
 *   sessionContext={sessionContext}
 *   objects={computes}
 *   isLoading={isLoading}
 *   ghostRows={ghostRows}
 *   onRequery={onRequery}
 * />
 */
import React, { useState, useEffect } from "react";

import { Loading, SortableHeader } from "@smarter/common";
import type { SessionContext, Sorting } from "@smarter/common";

import type { LLMHostCompute, LLMHostComputeListViewProps } from "@/lib/Types";
import { Toolbar } from "@/components/Toolbar";
import { StatusBar } from "@/components/StatusBar";
import { loggerPrefix } from "@/lib/const";
import { formatCpuMemory, formatGpus, formatPrice } from "@/lib/format";

import "@/components/ListView/styles.css";

/**
 * LoadingText
 *
 * Displays a muted "Loading..." text, used in skeleton rows to indicate loading state.
 */
const LoadingText = () => {
  return <span className="text-muted fw-semibold">Loading...</span>;
};

/**
 * TableHeader
 *
 * Renders the table header row, with a column title for each displayed field.
 * Its sortable columns sort the list, with the list api (see SortableHeader).
 */
const TableHeader = ({ sorting }: { sorting?: Sorting }) => {
  return (
    <thead className="table-light border-bottom-2">
      <tr className="">
        <SortableHeader column="name" sorting={sorting} className=" p-1">
          Name
        </SortableHeader>
        <SortableHeader column="instanceType" sorting={sorting} className="d-none d-lg-table-cell">
          Instance Type
        </SortableHeader>
        <SortableHeader column="gpuCount" sorting={sorting} className="">
          GPUs
        </SortableHeader>
        <SortableHeader column="cpu" sorting={sorting} className="d-none d-lg-table-cell">
          CPU and Memory
        </SortableHeader>
        <SortableHeader column="pricePerHour" sorting={sorting} className="d-none d-md-table-cell">
          Price per Node
        </SortableHeader>
        <th className="d-none d-md-table-cell">Node Group</th>
        <th className="">Operations</th>
      </tr>
    </thead>
  );
};

/**
 * LLMHostComputeRow
 *
 * Renders a single LLMHostCompute as a table row, displaying its details and action toolbar.
 *
 * @param compute - The LLMHostCompute to display.
 * @param sessionContext - Session context for actions.
 * @param onRequery - Callback to refresh the data after an action.
 */
const LLMHostComputeRow = React.memo(function LLMHostComputeRow({
  compute,
  sessionContext,
  onRequery,
}: {
  compute: LLMHostCompute;
  sessionContext: SessionContext;
  onRequery: () => void;
}) {
  return (
    <tr className="" key={compute.id}>
      {/* Name */}
      <td className="p-1 m-0">
        <a href={compute.manifestUrl} title={compute.description}>
          {compute.name}
        </a>
      </td>
      {/* Instance Type */}
      <td className="d-none d-lg-table-cell">{compute.instanceType}</td>
      {/* GPUs */}
      <td className="">{formatGpus(compute)}</td>
      {/* CPU and Memory */}
      <td className="d-none d-lg-table-cell">{formatCpuMemory(compute)}</td>
      {/* Price per Node */}
      <td className="d-none d-md-table-cell">{formatPrice(compute)}</td>
      {/* Node Group */}
      <td className="d-none d-md-table-cell ">
        <StatusBar compute={compute} />
      </td>
      {/* Actions */}
      <td className="text-end ">
        <Toolbar sessionContext={sessionContext} compute={compute} onRequery={onRequery} />
      </td>
    </tr>
  );
});

/**
 * LLMHostComputeRowGhost
 *
 * A skeleton row to display while the data is loading, with the same columns as LLMHostComputeRow.
 */
const LLMHostComputeRowGhost = React.memo(function LLMHostComputeRowGhost() {
  console.debug(`${loggerPrefix} Rendering LLMHostComputeRowGhost`);
  return (
    <tr className="ghost">
      {/* Name */}
      <td className="p-1 m-0">
        <Loading />
      </td>
      {/* Instance Type */}
      <td className="d-none d-lg-table-cell">
        <LoadingText />
      </td>
      {/* GPUs */}
      <td className=""></td>
      {/* CPU and Memory */}
      <td className="d-none d-lg-table-cell"></td>
      {/* Price per Node */}
      <td className="d-none d-md-table-cell"></td>
      {/* Node Group */}
      <td className="d-none d-md-table-cell "></td>
      {/* Actions */}
      <td className="text-end "></td>
    </tr>
  );
});

/**
 * LLMHostComputeRowGhosts
 *
 * Renders a number of skeleton rows to indicate loading state.
 *
 * @param count - Number of skeleton rows to render.
 */
const LLMHostComputeRowGhosts = React.memo(function LLMHostComputeRowGhosts({ count }: { count: number }) {
  console.debug(`${loggerPrefix} Rendering LLMHostComputeRowGhosts with count: ${count}`);
  return (
    <>
      {Array.from({ length: count }).map((_, idx) => (
        <LLMHostComputeRowGhost key={idx} />
      ))}
    </>
  );
});

/**
 * ChunkedRows
 *
 * Incrementally renders rows in chunks to avoid UI blocking.
 * Uses requestIdleCallback (if available) or setTimeout as a fallback to schedule rendering.
 *
 * @param computes - Array of LLMHostCompute objects to render.
 * @param sessionContext - Session context for actions.
 * @param onRequery - Callback to refresh the data.
 * @param chunkSize - Number of rows to render per chunk (default: 5).
 */
function ChunkedRows({
  computes,
  sessionContext,
  onRequery,
  chunkSize = 5,
}: {
  computes: LLMHostCompute[];
  sessionContext: SessionContext;
  onRequery: () => void;
  chunkSize?: number;
}) {
  const [visibleCount, setVisibleCount] = useState(chunkSize);

  useEffect(() => {
    if (visibleCount >= computes.length) return;
    const next = () => setVisibleCount((c) => Math.min(c + chunkSize, computes.length));
    if (window.requestIdleCallback) {
      const idleId = window.requestIdleCallback(next);
      return () => window.cancelIdleCallback(idleId);
    }
    const timeoutId = setTimeout(next, 0);
    return () => clearTimeout(timeoutId);
  }, [visibleCount, computes.length, chunkSize]);
  return (
    <>
      {computes.slice(0, visibleCount).map((compute) => (
        <LLMHostComputeRow key={compute.id} compute={compute} sessionContext={sessionContext} onRequery={onRequery} />
      ))}
    </>
  );
}

/**
 * ListView
 *
 * Main component for displaying a responsive, table-based list of LLMHostCompute resources.
 * Handles loading state with skeleton rows and incremental rendering for large lists.
 */
export function ListView({
  isLoading,
  ghostRows,
  sessionContext,
  objects,
  onRequery,
  sorting,
}: LLMHostComputeListViewProps) {
  console.debug(
    `${loggerPrefix} ListView() Rendering ListView - {isLoading: ${isLoading}, ghostRows: ${ghostRows}, objects length: ${Array.isArray(objects) ? objects.length : "N/A"}}`,
  );
  console.debug(`${loggerPrefix} SessionContext:`, sessionContext);
  console.debug(`${loggerPrefix} Objects:`, objects);
  return (
    <div className="table-responsive llmhost-compute-list-table-wrap ps-3 pe-3">
      <table className="table table-striped table-hover align-middle border">
        <TableHeader sorting={sorting} />
        <tbody>
          {isLoading ? (
            <LLMHostComputeRowGhosts count={ghostRows} />
          ) : (
            <ChunkedRows computes={objects} sessionContext={sessionContext} onRequery={onRequery} />
          )}
        </tbody>
      </table>
    </div>
  );
}

export default ListView;

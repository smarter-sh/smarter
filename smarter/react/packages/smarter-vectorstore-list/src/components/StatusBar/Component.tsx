/**
 * StatusBar React component: a Vectorstore's status, and indicators of how it is run.
 *
 * - its lifecycle status: pending, provisioning, ready, stopped, failed or deleting;
 * - deletion protection;
 * - whether it is inactive;
 * - scheduled snapshots, or backups.
 *
 * Usage:
 *   <StatusBar vectorstore={vectorstore} />
 */
import type { Vectorstore } from "@/lib/Types";
import { STATUS_BADGES } from "@/lib/format";

interface StatusbarProps {
  vectorstore: Vectorstore;
}

export const StatusBar = ({ vectorstore }: StatusbarProps) => {
  const badge = STATUS_BADGES[vectorstore.status] ?? STATUS_BADGES.pending;
  const maintenance = (vectorstore.spec?.maintenance ?? {}) as { snapshots?: boolean };
  const title = vectorstore.statusMessage ? `${badge.help} ${vectorstore.statusMessage}` : badge.help;
  return (
    <div className="statusbar d-flex align-items-center gap-2">
      <span className={`badge ${badge.className}`} title={title}>
        {badge.label}
      </span>
      {!vectorstore.isActive && (
        <span className="status-icon" title="Inactive: it may not be used.">
          <i className="bi bi-pause-circle text-secondary" />
        </span>
      )}
      {vectorstore.deletionProtection && (
        <span className="status-icon" title="Deletion protection: its database cannot be destroyed.">
          <i className="bi bi-shield-lock text-primary" />
        </span>
      )}
      {maintenance.snapshots !== false && (
        <span
          className="status-icon"
          title={`Scheduled snapshots: ${vectorstore.snapshotCount} kept${vectorstore.lastSnapshotAt ? `, the last at ${vectorstore.lastSnapshotAt}` : ""}.`}
        >
          <i className="bi bi-clock-history text-info" />
        </span>
      )}
    </div>
  );
};

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
import { gettext, interpolate } from "@smarter/common";

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
        <span className="status-icon" title={gettext("Inactive: it may not be used.")}>
          <i className="bi bi-pause-circle text-secondary" />
        </span>
      )}
      {vectorstore.deletionProtection && (
        <span className="status-icon" title={gettext("Deletion protection: its database cannot be destroyed.")}>
          <i className="bi bi-shield-lock text-primary" />
        </span>
      )}
      {maintenance.snapshots !== false && (
        <span
          className="status-icon"
          title={
            vectorstore.lastSnapshotAt
              ? interpolate(gettext("Scheduled snapshots: %(snapshotCount)s kept, the last at %(lastSnapshotAt)s."), {
                  snapshotCount: vectorstore.snapshotCount,
                  lastSnapshotAt: vectorstore.lastSnapshotAt,
                })
              : interpolate(gettext("Scheduled snapshots: %(snapshotCount)s kept."), {
                  snapshotCount: vectorstore.snapshotCount,
                })
          }
        >
          <i className="bi bi-clock-history text-info" />
        </span>
      )}
    </div>
  );
};

/**
 *
 * ExtensionStatusBar React component for displaying the status of an installed Extension.
 * Shows whether it is enabled, its trust badge, and where it was installed from, using icons and tooltips.
 *
 * Exports:
 *   - ExtensionStatusBar: Functional component that takes an Extension and renders its status indicators.
 *
 * Usage:
 *   <ExtensionStatusBar extension={extension} />
 */
import type { Extension } from "@/lib/Types";
import { gettext } from "@smarter/common";

interface ExtensionStatusBarProps {
  extension: Extension;
}

const TRUST_BADGE_ICONS: Record<Extension["trustBadge"], string> = {
  official: "bi bi-patch-check-fill text-primary",
  verified: "bi bi-patch-check text-success",
  community: "bi bi-people text-info",
  unverified: "bi bi-patch-question text-secondary",
};

export const ExtensionStatusBar = ({ extension }: ExtensionStatusBarProps) => {
  return (
    <div className="statusbar d-flex align-items-center gap-2">
      {/* Enabled */}
      <span
        className="status-icon"
        title={
          extension.enabled
            ? gettext("Enabled: its tools are offered to LLMs")
            : gettext("Disabled: its tools are offered once an administrator enables it")
        }
      >
        <i className={extension.enabled ? "bi bi-check-circle text-success" : "bi bi-x-circle text-secondary"} />
      </span>
      {/* Trust Badge */}
      <span className="status-icon" title={extension.trustBadgeLabel}>
        <i className={TRUST_BADGE_ICONS[extension.trustBadge] ?? TRUST_BADGE_ICONS.unverified} />
      </span>
      {/* Source */}
      <span
        className="status-icon"
        title={
          extension.source === "registry"
            ? gettext("Installed from the extension registry")
            : gettext("Installed from an upload")
        }
      >
        <i className={extension.source === "registry" ? "bi bi-cloud-download" : "bi bi-upload"} />
      </span>
    </div>
  );
};

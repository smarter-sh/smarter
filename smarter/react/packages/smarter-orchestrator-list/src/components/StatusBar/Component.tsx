/**
 *
 * StatusBar React component for displaying the status of a Orchestrator instance.
 * Shows readiness, deployment, authentication, DNS, TLS, subdomain, and custom domain status using icons and tooltips.
 *
 * Exports:
 *   - StatusBar: Functional component that takes a Orchestrator and renders its status indicators.
 *
 * Usage:
 *   <StatusBar orchestrator={orchestrator} />
 */
import type { Orchestrator } from "@/lib/Types";
import { gettext } from "@smarter/common";
interface StatusbarProps {
  orchestrator: Orchestrator;
}

export const StatusBar = ({ orchestrator }: StatusbarProps) => {
  return (
    <div className="statusbar d-flex align-items-center gap-2">
      {/* Ready */}
      <span
        className="status-icon"
        title={
          orchestrator.ready
            ? gettext("Ready: Orchestrator is ready to serve requests")
            : gettext("Not ready: Orchestrator is initializing")
        }
      >
        <i className={orchestrator.ready ? "bi bi-check-circle text-success" : "bi bi-x-circle text-secondary"} />
      </span>
      {/* Deployed */}
      <span className="status-icon" title={gettext("Deployed: Orchestrator is deployed")}>
        <i className="bi bi-cloud-check" />
      </span>
      {/* Authentication Required */}
      <span className="status-icon" title={gettext("Authentication required to access this orchestrator")}>
        <i className="bi bi-lock" />
      </span>
      {/* DNS Verification */}
      <span className="status-icon" title={gettext("DNS verified")}>
        <i className="bi bi-globe" />
      </span>
      {/* TLS Certificate */}
      <span className="status-icon" title={gettext("TLS certificate issued")}>
        <i className="bi bi-shield-lock" />
      </span>
      {/* Subdomain */}
      <span className="status-icon" title={gettext("Subdomain: example.com")}>
        <i className="bi bi-link-45deg text-info" />
      </span>
      {/* Custom Domain */}
      <span className="status-icon" title={gettext("Custom domain: example.com")}>
        <i className="bi bi-link text-info" />
      </span>
    </div>
  );
};

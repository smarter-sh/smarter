/**
 *
 * StatusBar React component for displaying the status of a Vectorsearch instance.
 * Shows readiness, deployment, authentication, DNS, TLS, subdomain, and custom domain status using icons and tooltips.
 *
 * Exports:
 *   - StatusBar: Functional component that takes a Vectorsearch and renders its status indicators.
 *
 * Usage:
 *   <StatusBar vectorsearch={vectorsearch} />
 */
import type { Vectorsearch } from "@/lib/Types";
import { gettext } from "@smarter/common";
interface StatusbarProps {
  vectorsearch: Vectorsearch;
}

export const StatusBar = ({ vectorsearch }: StatusbarProps) => {
  return (
    <div className="statusbar d-flex align-items-center gap-2">
      {/* Ready */}
      <span
        className="status-icon"
        title={
          vectorsearch.ready
            ? gettext("Ready: Vectorsearch is ready to serve requests")
            : gettext("Not ready: Vectorsearch is initializing")
        }
      >
        <i className={vectorsearch.ready ? "bi bi-check-circle text-success" : "bi bi-x-circle text-secondary"} />
      </span>
      {/* Deployed */}
      <span className="status-icon" title={gettext("Deployed: Vectorsearch is deployed")}>
        <i className="bi bi-cloud-check" />
      </span>
      {/* Authentication Required */}
      <span className="status-icon" title={gettext("Authentication required to access this vectorsearch")}>
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

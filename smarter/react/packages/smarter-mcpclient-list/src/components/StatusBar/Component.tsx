/**
 *
 * StatusBar React component for displaying the status of a MCPClient instance.
 * Shows readiness, deployment, authentication, DNS, TLS, subdomain, and custom domain status using icons and tooltips.
 *
 * Exports:
 *   - StatusBar: Functional component that takes a MCPClient and renders its status indicators.
 *
 * Usage:
 *   <StatusBar mcpclient={mcpclient} />
 */
import type { MCPClient } from "@/lib/Types";
interface StatusbarProps {
  mcpclient: MCPClient;
}

export const StatusBar = ({ mcpclient }: StatusbarProps) => {
  return (
    <div className="statusbar d-flex align-items-center gap-2">
      {/* Ready */}
      <span
        className="status-icon"
        title={mcpclient.ready ? "Ready: MCPClient is ready to serve requests" : "Not ready: MCPClient is initializing"}
      >
        <i className={mcpclient.ready ? "bi bi-check-circle text-success" : "bi bi-x-circle text-secondary"} />
      </span>
      {/* Deployed */}
      <span className="status-icon" title="Deployed: MCPClient is deployed">
        <i className="bi bi-cloud-check" />
      </span>
      {/* Authentication Required */}
      <span
        className="status-icon"
        title="Authentication required to access this mcpclient"
      >
        <i className="bi bi-lock" />
      </span>
      {/* DNS Verification */}
      <span
        className="status-icon"
        title="DNS verified"
      >
        <i className="bi bi-globe" />
      </span>
      {/* TLS Certificate */}
      <span
        className="status-icon"
        title="TLS certificate issued"
      >
        <i
          className="bi bi-shield-lock"
        />
      </span>
      {/* Subdomain */}
        <span className="status-icon" title={"Subdomain: example.com"}>
          <i className="bi bi-link-45deg text-info" />
        </span>
      {/* Custom Domain */}
        <span className="status-icon" title={"Custom domain: example.com"}>
          <i className="bi bi-link text-info" />
        </span>
    </div>
  );
};

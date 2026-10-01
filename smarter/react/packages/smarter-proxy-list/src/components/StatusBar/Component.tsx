/**
 *
 * StatusBar React component for displaying the state of a Proxy: whether it is active, whether
 * it has an API key to send, and whether it restricts the paths that callers may use.
 *
 * Exports:
 *   - StatusBar: Functional component that takes a Proxy and renders its status indicators.
 *
 * Usage:
 *   <StatusBar proxy={proxy} />
 */
import type { Proxy } from "@/lib/Types";
import { formatAllowedPaths, formatApiKey } from "@/lib/format";

interface StatusbarProps {
  proxy: Proxy;
}

export const StatusBar = ({ proxy }: StatusbarProps) => {
  const restricted = proxy.allowedPaths?.length > 0;
  return (
    <div className="statusbar d-flex align-items-center gap-2">
      {/* Active */}
      <span
        className="status-icon"
        title={proxy.isActive ? "Active: the Proxy forwards requests." : "Inactive: the Proxy refuses every request."}
      >
        <i className={proxy.isActive ? "bi bi-check-circle text-success" : "bi bi-pause-circle text-secondary"} />
      </span>
      {/* API key */}
      <span
        className="status-icon"
        title={
          proxy.apiKeySecretName
            ? `API key: Secret ${formatApiKey(proxy)}, sent in ${proxy.authHeader}.`
            : "No API key: set the Proxy's spec.apiKey, or its Provider's API key. Requests are refused."
        }
      >
        <i className={proxy.apiKeySecretName ? "bi bi-key text-success" : "bi bi-key text-danger"} />
      </span>
      {/* Allowed paths */}
      <span
        className="status-icon"
        title={
          restricted
            ? `Allowed paths: ${proxy.allowedPaths.join(", ")}`
            : "All paths are allowed: callers may use every endpoint of the provider's API with this API key."
        }
      >
        <i className={restricted ? "bi bi-shield-check text-info" : "bi bi-shield-exclamation text-warning"} />{" "}
        <small>{formatAllowedPaths(proxy)}</small>
      </span>
    </div>
  );
};

import type { LLMClient } from "@/lib/Types";
/**
 * @file Component.tsx
 * @module StatusBar/Component
 *
 * StatusBar React component for displaying the status of a LLMClient instance.
 * Shows readiness, deployment, authentication, DNS, TLS, subdomain, and custom domain status using icons and tooltips.
 *
 * Exports:
 *   - StatusBar: Functional component that takes a LLMClient and renders its status indicators.
 *
 * Usage:
 *   <StatusBar llm_client={llm_client} />
 */
interface StatusbarProps {
  llm_client: LLMClient;
}

export const StatusBar = ({ llm_client }: StatusbarProps) => {
  return (
    <div className="statusbar d-flex align-items-center gap-2">
      {/* Ready */}
      <span
        className="status-icon"
        title={llm_client.ready ? "Ready: LLMClient is ready to serve requests" : "Not ready: LLMClient is initializing"}
      >
        <i className={llm_client.ready ? "bi bi-check-circle text-success" : "bi bi-x-circle text-secondary"} />
      </span>
      {/* Deployed */}
      <span className="status-icon" title={llm_client.deployed ? "Deployed: LLMClient is deployed" : "Not deployed"}>
        <i className={llm_client.deployed ? "bi bi-cloud-check" : "bi bi-cloud-slash"} />
      </span>
      {/* Authentication Required */}
      <span
        className="status-icon"
        title={
          llm_client.isAuthenticationRequired
            ? "Authentication required to access this llm_client"
            : "No authentication required"
        }
      >
        <i className={llm_client.isAuthenticationRequired ? "bi bi-lock" : "bi bi-unlock"} />
      </span>
      {/* DNS Verification */}
      <span
        className="status-icon"
        title={llm_client.dnsVerificationStatus === "verified" ? "DNS verified" : "DNS verification pending or failed"}
      >
        <i className={llm_client.dnsVerificationStatus === "verified" ? "bi bi-globe" : "bi bi-exclamation-circle"} />
      </span>
      {/* TLS Certificate */}
      <span
        className="status-icon"
        title={
          llm_client.tlsCertificateIssuanceStatus === "issued"
            ? "TLS certificate issued"
            : "TLS certificate pending or failed"
        }
      >
        <i
          className={
            llm_client.tlsCertificateIssuanceStatus === "issued" ? "bi bi-shield-lock" : "bi bi-shield-exclamation"
          }
        />
      </span>
      {/* Subdomain */}
      {llm_client.subdomain && (
        <span className="status-icon" title={`Subdomain: ${llm_client.subdomain}`}>
          <i className="bi bi-link-45deg text-info" />
        </span>
      )}
      {/* Custom Domain */}
      {llm_client.customDomain && (
        <span className="status-icon" title={`Custom domain: ${llm_client.customDomain}`}>
          <i className="bi bi-link text-info" />
        </span>
      )}
    </div>
  );
};

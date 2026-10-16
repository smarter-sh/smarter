import type { LLMClient } from "@/lib/Types";
import { gettext, interpolate } from "@smarter/common";
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
 *   <StatusBar llmclient={llmclient} />
 */
interface StatusbarProps {
  llmclient: LLMClient;
}

export const StatusBar = ({ llmclient }: StatusbarProps) => {
  return (
    <div className="statusbar d-flex align-items-center gap-2">
      {/* Ready */}
      <span
        className="status-icon"
        title={
          llmclient.ready
            ? gettext("Ready: LLMClient is ready to serve requests")
            : gettext("Not ready: LLMClient is initializing")
        }
      >
        <i className={llmclient.ready ? "bi bi-check-circle text-success" : "bi bi-x-circle text-secondary"} />
      </span>
      {/* Deployed */}
      <span
        className="status-icon"
        title={llmclient.deployed ? gettext("Deployed: LLMClient is deployed") : gettext("Not deployed")}
      >
        <i className={llmclient.deployed ? "bi bi-cloud-check" : "bi bi-cloud-slash"} />
      </span>
      {/* Authentication Required */}
      <span
        className="status-icon"
        title={
          llmclient.isAuthenticationRequired
            ? gettext("Authentication required to access this llmclient")
            : gettext("No authentication required")
        }
      >
        <i className={llmclient.isAuthenticationRequired ? "bi bi-lock" : "bi bi-unlock"} />
      </span>
      {/* DNS Verification */}
      <span
        className="status-icon"
        title={
          llmclient.dnsVerificationStatus === "verified"
            ? gettext("DNS verified")
            : gettext("DNS verification pending or failed")
        }
      >
        <i className={llmclient.dnsVerificationStatus === "verified" ? "bi bi-globe" : "bi bi-exclamation-circle"} />
      </span>
      {/* TLS Certificate */}
      <span
        className="status-icon"
        title={
          llmclient.tlsCertificateIssuanceStatus === "issued"
            ? gettext("TLS certificate issued")
            : gettext("TLS certificate pending or failed")
        }
      >
        <i
          className={
            llmclient.tlsCertificateIssuanceStatus === "issued" ? "bi bi-shield-lock" : "bi bi-shield-exclamation"
          }
        />
      </span>
      {/* Subdomain */}
      {llmclient.subdomain && (
        <span
          className="status-icon"
          title={interpolate(gettext("Subdomain: %(subdomain)s"), { subdomain: llmclient.subdomain })}
        >
          <i className="bi bi-link-45deg text-info" />
        </span>
      )}
      {/* Custom Domain */}
      {llmclient.customDomain && (
        <span
          className="status-icon"
          title={interpolate(gettext("Custom domain: %(customDomain)s"), { customDomain: llmclient.customDomain })}
        >
          <i className="bi bi-link text-info" />
        </span>
      )}
    </div>
  );
};

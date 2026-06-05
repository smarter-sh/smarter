import type { Chatbot } from "@/lib/Types";
/**
 * @file Component.tsx
 * @module StatusBar/Component
 *
 * StatusBar React component for displaying the status of a Chatbot instance.
 * Shows readiness, deployment, authentication, DNS, TLS, subdomain, and custom domain status using icons and tooltips.
 *
 * Exports:
 *   - StatusBar: Functional component that takes a Chatbot and renders its status indicators.
 *
 * Usage:
 *   <StatusBar chatbot={chatbot} />
 */
interface StatusbarProps {
  chatbot: Chatbot;
}

export const StatusBar = ({ chatbot }: StatusbarProps) => {
  return (
    <div className="statusbar d-flex align-items-center gap-2">
      {/* Ready */}
      <span
        className="status-icon"
        title={chatbot.ready ? "Ready: Chatbot is ready to serve requests" : "Not ready: Chatbot is initializing"}
      >
        <i className={chatbot.ready ? "bi bi-check-circle text-success" : "bi bi-x-circle text-secondary"} />
      </span>
      {/* Deployed */}
      <span className="status-icon" title={chatbot.deployed ? "Deployed: Chatbot is deployed" : "Not deployed"}>
        <i className={chatbot.deployed ? "bi bi-cloud-check" : "bi bi-cloud-slash"} />
      </span>
      {/* Authentication Required */}
      <span
        className="status-icon"
        title={
          chatbot.isAuthenticationRequired
            ? "Authentication required to access this chatbot"
            : "No authentication required"
        }
      >
        <i className={chatbot.isAuthenticationRequired ? "bi bi-lock" : "bi bi-unlock"} />
      </span>
      {/* DNS Verification */}
      <span
        className="status-icon"
        title={chatbot.dnsVerificationStatus === "verified" ? "DNS verified" : "DNS verification pending or failed"}
      >
        <i className={chatbot.dnsVerificationStatus === "verified" ? "bi bi-globe" : "bi bi-exclamation-circle"} />
      </span>
      {/* TLS Certificate */}
      <span
        className="status-icon"
        title={
          chatbot.tlsCertificateIssuanceStatus === "issued"
            ? "TLS certificate issued"
            : "TLS certificate pending or failed"
        }
      >
        <i
          className={
            chatbot.tlsCertificateIssuanceStatus === "issued" ? "bi bi-shield-lock" : "bi bi-shield-exclamation"
          }
        />
      </span>
      {/* Subdomain */}
      {chatbot.subdomain && (
        <span className="status-icon" title={`Subdomain: ${chatbot.subdomain}`}>
          <i className="bi bi-link-45deg text-info" />
        </span>
      )}
      {/* Custom Domain */}
      {chatbot.customDomain && (
        <span className="status-icon" title={`Custom domain: ${chatbot.customDomain}`}>
          <i className="bi bi-link text-info" />
        </span>
      )}
    </div>
  );
};

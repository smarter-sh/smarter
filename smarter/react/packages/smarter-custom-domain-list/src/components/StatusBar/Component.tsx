/**
 *
 * StatusBar React component for displaying the status of a CustomDomain instance.
 * Shows whether an llmclient uses the domain, whether that llmclient is deployed, and the
 * number of DNS records, using icons and tooltips. The verification status is shown by
 * VerificationBadge.
 *
 * Exports:
 *   - StatusBar: Functional component that takes a CustomDomain and renders its status indicators.
 *
 * Usage:
 *   <StatusBar customDomain={customDomain} />
 */
import type { CustomDomain } from "@/lib/Types";
import { gettext, interpolate, ngettext } from "@smarter/common";
interface StatusbarProps {
  customDomain: CustomDomain;
}

export const StatusBar = ({ customDomain }: StatusbarProps) => {
  const llmclient = customDomain.llmclient;
  const recordCount = customDomain.dnsRecords?.length || 0;
  return (
    <div className="statusbar d-flex align-items-center gap-2">
      {/* LLMClient */}
      <span
        className="status-icon"
        title={
          llmclient
            ? interpolate(gettext("LLMClient: %(name)s"), { name: llmclient.name })
            : gettext("No LLMClient uses this domain")
        }
      >
        <i className={llmclient ? "bi bi-robot text-info" : "bi bi-robot text-secondary"} />
      </span>
      {/* Deployed */}
      <span
        className="status-icon"
        title={llmclient?.deployed ? gettext("Deployed: the LLMClient is deployed") : gettext("Not deployed")}
      >
        <i className={llmclient?.deployed ? "bi bi-cloud-check text-success" : "bi bi-cloud text-secondary"} />
      </span>
      {/* DNS Records */}
      <span
        className="status-icon"
        title={interpolate(ngettext("%(recordCount)s DNS record", "%(recordCount)s DNS records", recordCount), {
          recordCount,
        })}
      >
        <i className="bi bi-globe" /> <small>{recordCount}</small>
      </span>
    </div>
  );
};

/**
 * The selected LLM provider's card, under the request editor.
 *
 * The header identifies the provider: its logo, its name (a link to its page in the web console), its
 * version and verification status, and its description, with links to its website, docs, terms of
 * service and privacy policy. The body shows its flags as chips, then its details in four groups:
 * how Smarter connects to it, who owns it, its terms of service, and whom to contact. Tags and
 * annotations follow. Values that a provider doesn't have say so, rather than leave a gap.
 *
 * :param provider: The selected provider, or null while the providers load.
 * :type provider: LLMProvider | null
 *
 * :returns: The provider's card, or nothing without a provider.
 * :rtype: JSX.Element | null
 */
import type { LLMProvider } from "@/components/LLMProviders";
import ProviderDetails from "@/components/LLMProviderMetaData/ProviderDetails";
import ProviderFlags from "@/components/LLMProviderMetaData/ProviderFlags";
import ProviderLinks from "@/components/LLMProviderMetaData/ProviderLinks";
import { gettext, interpolate } from "@smarter/common";

import "@/components/LLMProviderMetaData/styles.css";

interface ProviderMetaDataProps {
  provider: LLMProvider | null;
}

interface StatusInfo {
  label: string;
  color: string;
}

/** The label and Keen color of each ProviderStatus, by its value. An unknown status shows as it is, in gray. */
const STATUSES: Record<string, StatusInfo> = {
  unverified: { label: gettext("Unverified"), color: "secondary" },
  verifying: { label: gettext("Verifying"), color: "info" },
  failed: { label: gettext("Verification failed"), color: "danger" },
  verified: { label: gettext("Verified"), color: "success" },
  suspended: { label: gettext("Suspended"), color: "danger" },
  deprecated: { label: gettext("Deprecated"), color: "warning" },
};

function StatusBadge({ status }: { status: string }) {
  const info = STATUSES[status] ?? { label: status, color: "secondary" };
  return (
    <span className={`badge badge-light-${info.color} fs-8 fw-bold px-2 py-1 text-nowrap`}>
      <span className={`bullet bullet-dot bg-${info.color} h-5px w-5px me-1`}></span>
      {info.label}
    </span>
  );
}

/** The provider's logo, on a dark tile: the logos that providers publish are mostly white. Its initial without one. */
function ProviderLogo({ provider }: { provider: LLMProvider }) {
  if (!provider.logo) {
    return (
      <div className="provider-meta-logo" aria-hidden="true">
        <span className="provider-meta-logo-initial">{provider.name.charAt(0).toUpperCase()}</span>
      </div>
    );
  }
  return (
    <div className="provider-meta-logo">
      <img src={provider.logo} alt={interpolate(gettext("%(name)s logo"), { name: provider.name })} />
    </div>
  );
}

export default function LLMProviderMetaData({ provider }: ProviderMetaDataProps) {
  if (!provider) {
    return null;
  }

  return (
    <section className="col-12 mt-5" aria-label={provider.name}>
      <div className="card card-flush shadow-sm">
        <div className="card-header align-items-start flex-wrap gap-3 pt-6">
          <div className="d-flex align-items-center gap-4 min-w-0">
            <ProviderLogo provider={provider} />
            <div className="d-flex flex-column min-w-0">
              <div className="d-flex flex-wrap align-items-center gap-2">
                <h3 className="fw-bold text-gray-900 fs-3 m-0">
                  {provider.manifestUrl ? (
                    <a href={provider.manifestUrl} className="text-gray-900 text-hover-primary">
                      {provider.name}
                    </a>
                  ) : (
                    provider.name
                  )}
                </h3>
                <span className="badge badge-light fs-8 fw-semibold text-gray-600">v{provider.version}</span>
                <StatusBadge status={provider.status} />
              </div>
              {provider.description && (
                <span className="text-gray-600 fw-semibold fs-7 mt-1">{provider.description}</span>
              )}
            </div>
          </div>
          <div className="card-toolbar m-0">
            <ProviderLinks provider={provider} />
          </div>
        </div>
        <div className="card-body pt-4 provider-meta-body">
          <ProviderFlags provider={provider} />
          <ProviderDetails provider={provider} />
        </div>
      </div>
    </section>
  );
}

/**
 * DetailView React Component
 *
 * The Details tab of a provider's detail, which the list opens when one of its rows is chosen (see TabbedListView
 * and ResourceDetail in @smarter/common): the provider's description, status and actions, then how Smarter
 * connects to it, the flags that the platform keeps about it, who publishes it, the acceptance of its terms of
 * service, and the metadata that every resource has. Its API key is shown by the name of the Secret that holds it,
 * never by its value.
 *
 * Props:
 * - sessionContext (SessionContext): Authentication and API context for the actions.
 * - object (Provider): The provider.
 * - onRequery (function): Reloads the list, after an action changes it.
 * - filtering (Filtering): Narrows the list by a tag or annotation that is clicked.
 *
 * Usage:
 * <DetailView sessionContext={sessionContext} object={provider} onRequery={onRequery} filtering={filtering} />
 */
import {
  DetailField,
  DetailOverview,
  DetailSection,
  DetailValue,
  gettext,
  ResourceMetadataSection,
} from "@smarter/common";

import type { ProviderDetailViewProps } from "@/lib/Types";
import { Toolbar } from "@/components/Toolbar";

function DetailView({ sessionContext, object: provider, onRequery, filtering }: ProviderDetailViewProps) {
  return (
    <>
      <DetailOverview description={provider.description}>
        {provider.status && <span className="badge badge-light-primary fw-semibold">{provider.status}</span>}
        <span className={`badge ${provider.isActive ? "badge-light-success" : "badge-light"} fw-semibold`}>
          {provider.isActive ? gettext("Active") : gettext("Inactive")}
        </span>
        {provider.isSuspended && <span className="badge badge-light-danger fw-semibold">{gettext("Suspended")}</span>}
        {provider.isDeprecated && (
          <span className="badge badge-light-warning fw-semibold">{gettext("Deprecated")}</span>
        )}
        <Toolbar sessionContext={sessionContext} provider={provider} onRequery={onRequery} />
      </DetailOverview>

      <DetailSection title={gettext("Connectivity")} icon="technology-4">
        <DetailField label={gettext("Base URL")} value={provider.baseUrl} type="url" wide />
        <DetailField
          label={gettext("API key")}
          help={gettext("The Secret that holds the provider's API key. Its value is never shown.")}
        >
          {provider.apiKey ? (
            <a href={provider.apiKey.manifestUrl} className="smarter-detail-link">
              <i className="ki-outline ki-lock-2 fs-7 me-1" aria-hidden="true" />
              {provider.apiKey.name}
            </a>
          ) : (
            <DetailValue value={null} />
          )}
        </DetailField>
        <DetailField label={gettext("Default model")} value={provider.defaultModel} type="code" />
        <DetailField
          label={gettext("Connectivity test path")}
          value={provider.connectivityTestPath}
          type="code"
          help={gettext(
            "The path, relative to the base URL, that is requested to test that the provider is reachable.",
          )}
        />
        <DetailField
          label={gettext("Ready")}
          value={provider.ready}
          type="bool"
          help={gettext("Whether the provider can serve requests.")}
        />
        <DetailField label={gettext("Last accessed")} value={provider.lastAccessed} type="dateTime" />
        <DetailField label={gettext("Expires")} value={provider.expiresAt} type="dateTime" />
      </DetailSection>

      <DetailSection title={gettext("Status")} icon="shield-tick">
        <DetailField label={gettext("Status")} value={provider.status} />
        <DetailField label={gettext("Active")} value={provider.isActive} type="bool" />
        <DetailField
          label={gettext("Verified")}
          value={provider.isVerified}
          type="bool"
          help={gettext("Whether the provider passed its verification checks.")}
        />
        <DetailField
          label={gettext("Default")}
          value={provider.isDefault}
          type="bool"
          help={gettext("Whether this is the provider that is used when none is named.")}
        />
        <DetailField
          label={gettext("Official provider")}
          value={provider.isOfficialProvider}
          type="bool"
          help={gettext("Whether the provider belongs to the platform's administrator, rather than to an account.")}
        />
        <DetailField label={gettext("Featured")} value={provider.isFeatured} type="bool" />
        <DetailField label={gettext("Deprecated")} value={provider.isDeprecated} type="bool" />
        <DetailField label={gettext("Flagged")} value={provider.isFlagged} type="bool" />
        <DetailField label={gettext("Suspended")} value={provider.isSuspended} type="bool" />
      </DetailSection>

      <DetailSection title={gettext("Publisher")} icon="book-open">
        <DetailField label={gettext("Website")} value={provider.websiteUrl} type="url" />
        <DetailField label={gettext("Documentation")} value={provider.docsUrl} type="url" />
        <DetailField label={gettext("Terms of service")} value={provider.termsOfServiceUrl} type="url" />
        <DetailField label={gettext("Privacy policy")} value={provider.privacyPolicyUrl} type="url" />
        <DetailField label={gettext("Logo")} value={provider.logo} type="url" />
        <DetailField label={gettext("Contact email")} value={provider.contactEmail} />
        <DetailField label={gettext("Contact email verified")} value={provider.contactEmailVerified} type="dateTime" />
        <DetailField label={gettext("Support email")} value={provider.supportEmail} />
        <DetailField label={gettext("Support email verified")} value={provider.supportEmailVerified} type="dateTime" />
        <DetailField label={gettext("Ownership requested")} value={provider.ownershipRequested} type="json" wide />
      </DetailSection>

      <DetailSection title={gettext("Terms of service")} icon="document">
        <DetailField
          label={gettext("Accepted")}
          value={provider.tosAccepted}
          type="bool"
          help={gettext("Whether someone in the account accepted the provider's terms of service.")}
        />
        <DetailField label={gettext("Accepted at")} value={provider.tosAcceptedAt} type="dateTime" />
        <DetailField label={gettext("Accepted by")} value={provider.tosAcceptedBy?.username} />
      </DetailSection>

      <ResourceMetadataSection resource={provider} filtering={filtering}>
        <DetailField label={gettext("RFC 1034 compliant name")} value={provider.rfc1034CompliantName} type="code" />
      </ResourceMetadataSection>
    </>
  );
}

export default DetailView;

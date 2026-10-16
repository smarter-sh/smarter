/**
 * CardView React Component
 *
 * This component renders provider resources as individual cards, displaying detailed information and actions for each provider.
 * It is used to present providers in a card-based layout, with modals for clone, rename, and delete actions.
 *
 * Features:
 * - Displays provider details in a visually distinct card format.
 * - Integrates action buttons for open, edit, clone, rename, and delete operations.
 * - Uses modal dialogs for clone, rename, and delete workflows (scaffolded for further logic).
 * - Supports a custom detail row renderer for flexible display of provider attributes.
 * - Accepts a custom CSS class for layout control.
 *
 * Props:
 * - sessionContext (SessionContext): Authentication and API context for actions.
 * - title (string): Title displayed above the card list.
 * - providers (Provider[]): Array of provider objects to display.
 * - renderDetailRow (function): Function to render detail rows for provider attributes.
 *
 * Usage:
 * <CardView sessionContext={sessionContext} title="Your Providers" objects={providers} renderDetailRow={renderDetailRow} />
 *
 * This component is intended for use in views where objects are presented in a card/grid format.
 */
import type { ProviderCardViewProps } from "@/lib/Types";
import { loggerPrefix } from "@/lib/const";
import { Toolbar } from "@/components/Toolbar";
import { StatusBar } from "@/components/StatusBar";
import { renderDetailRow } from "@/components/CardView/renderDetail";

import "@/components/CardView/styles.css";
import { gettext } from "@smarter/common";

function CardView({ sessionContext, objects, onRequery }: ProviderCardViewProps) {
  console.debug(loggerPrefix, "Rendering CardView with objects:", objects, sessionContext);

  return (
    <div className="row g-4 p-4">
      {Array.isArray(objects) &&
        objects.map((provider) => (
          <div className="col-12" key={provider.id}>
            <div className="card h-100">
              <div className="card-header d-flex justify-content-between align-items-center bg-white border-bottom-0 pb-0">
                <Toolbar sessionContext={sessionContext} provider={provider} onRequery={onRequery} />
                <span className="border rounded p-2">
                  <StatusBar provider={provider} />
                </span>
              </div>
              <div className="card-body">
                <h5 className="card-title mb-3 text-primary fw-bold text-center">
                  <a href={provider.manifestUrl} className="text-decoration-none text-primary">
                    {provider.name}
                  </a>
                </h5>
                <table className="table table-bordered table-sm align-middle mb-0">
                  <tbody>
                    {renderDetailRow(gettext("ID"), provider.id, "number")}
                    {renderDetailRow(gettext("Status"), provider.status)}
                    {renderDetailRow(gettext("Manifest URL"), provider.manifestUrl, "url")}
                    {renderDetailRow(gettext("Base URL"), provider.baseUrl, "url")}
                    {renderDetailRow(gettext("Owner"), provider.userProfile?.user?.username)}
                    {renderDetailRow(gettext("Owner Email"), provider.userProfile?.user?.email)}
                    {renderDetailRow(gettext("Account Number"), provider.userProfile?.account?.accountNumber)}
                    {renderDetailRow(gettext("Created"), provider.createdAt, "dateTime")}
                    {renderDetailRow(gettext("Last Updated"), provider.updatedAt, "dateTime")}
                    {renderDetailRow(gettext("Version"), provider.version)}
                    {renderDetailRow(gettext("Default Model"), provider.defaultModel)}
                    {renderDetailRow(gettext("Connectivity Test Path"), provider.connectivityTestPath)}
                    {renderDetailRow(gettext("Description"), provider.description)}
                    {renderDetailRow(gettext("Tags"), provider.tags, "str[]")}
                    {renderDetailRow(gettext("Annotations"), provider.annotations, "json")}
                    {renderDetailRow(gettext("Ready"), provider.ready, "bool")}
                    {renderDetailRow(gettext("Is Default"), provider.isDefault, "bool")}
                    {renderDetailRow(gettext("Is Active"), provider.isActive, "bool")}
                    {renderDetailRow(gettext("Is Verified"), provider.isVerified, "bool")}
                    {renderDetailRow(gettext("Is Featured"), provider.isFeatured, "bool")}
                    {renderDetailRow(gettext("Is Deprecated"), provider.isDeprecated, "bool")}
                    {renderDetailRow(gettext("Is Flagged"), provider.isFlagged, "bool")}
                    {renderDetailRow(gettext("Is Suspended"), provider.isSuspended, "bool")}
                    {renderDetailRow(gettext("Logo"), provider.logo, "url")}
                    {renderDetailRow(gettext("Website"), provider.websiteUrl, "url")}
                    {renderDetailRow(gettext("Docs URL"), provider.docsUrl, "url")}
                    {renderDetailRow(gettext("Terms Of Service URL"), provider.termsOfServiceUrl, "url")}
                    {renderDetailRow(gettext("Privacy Policy URL"), provider.privacyPolicyUrl, "url")}
                    {renderDetailRow(gettext("Contact Email"), provider.contactEmail)}
                    {renderDetailRow(gettext("Contact Email Verified"), provider.contactEmailVerified, "dateTime")}
                    {renderDetailRow(gettext("Support Email"), provider.supportEmail)}
                    {renderDetailRow(gettext("Support Email Verified"), provider.supportEmailVerified, "dateTime")}
                    {renderDetailRow(gettext("Ownership Requested"), provider.ownershipRequested, "json")}
                    {renderDetailRow(gettext("Expires At"), provider.expiresAt, "dateTime")}
                    {renderDetailRow(gettext("Last Accessed"), provider.lastAccessed, "dateTime")}
                    {renderDetailRow(gettext("API Key"), provider.apiKey, "json")}
                    {renderDetailRow(gettext("Is Official Provider"), provider.isOfficialProvider, "bool")}
                    {renderDetailRow(gettext("TOS Accepted"), provider.tosAccepted, "bool")}
                    {renderDetailRow(gettext("TOS Accepted At"), provider.tosAcceptedAt, "dateTime")}
                    {renderDetailRow(
                      gettext("TOS Accepted By"),
                      provider.tosAcceptedBy ? provider.tosAcceptedBy.username : null,
                    )}
                    {renderDetailRow(gettext("RFC 1034 Compliant Name"), provider.rfc1034CompliantName)}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        ))}
    </div>
  );
}

export default CardView;

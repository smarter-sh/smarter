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

import "./styles.css";

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
                    {renderDetailRow("ID", provider.id, "number")}
                    {renderDetailRow("Status", provider.status)}
                    {renderDetailRow("Manifest URL", provider.manifestUrl, "url")}
                    {renderDetailRow("Base URL", provider.baseUrl, "url")}
                    {renderDetailRow("Owner", provider.userProfile?.user?.username)}
                    {renderDetailRow("Owner Email", provider.userProfile?.user?.email)}
                    {renderDetailRow("Account Number", provider.userProfile?.account?.accountNumber)}
                    {renderDetailRow("Created", provider.createdAt, "dateTime")}
                    {renderDetailRow("Last Updated", provider.updatedAt, "dateTime")}
                    {renderDetailRow("Version", provider.version)}
                    {renderDetailRow("Default Model", provider.defaultModel)}
                    {renderDetailRow("Connectivity Test Path", provider.connectivityTestPath)}
                    {renderDetailRow("Description", provider.description)}
                    {renderDetailRow("Tags", provider.tags, "str[]")}
                    {renderDetailRow("Annotations", provider.annotations, "json")}
                    {renderDetailRow("Ready", provider.ready, "bool")}
                    {renderDetailRow("Is Default", provider.isDefault, "bool")}
                    {renderDetailRow("Is Active", provider.isActive, "bool")}
                    {renderDetailRow("Is Verified", provider.isVerified, "bool")}
                    {renderDetailRow("Is Featured", provider.isFeatured, "bool")}
                    {renderDetailRow("Is Deprecated", provider.isDeprecated, "bool")}
                    {renderDetailRow("Is Flagged", provider.isFlagged, "bool")}
                    {renderDetailRow("Is Suspended", provider.isSuspended, "bool")}
                    {renderDetailRow("Logo", provider.logo, "url")}
                    {renderDetailRow("Website", provider.websiteUrl, "url")}
                    {renderDetailRow("Docs URL", provider.docsUrl, "url")}
                    {renderDetailRow("Terms Of Service URL", provider.termsOfServiceUrl, "url")}
                    {renderDetailRow("Privacy Policy URL", provider.privacyPolicyUrl, "url")}
                    {renderDetailRow("Contact Email", provider.contactEmail)}
                    {renderDetailRow("Contact Email Verified", provider.contactEmailVerified, "dateTime")}
                    {renderDetailRow("Support Email", provider.supportEmail)}
                    {renderDetailRow("Support Email Verified", provider.supportEmailVerified, "dateTime")}
                    {renderDetailRow("Ownership Requested", provider.ownershipRequested, "json")}
                    {renderDetailRow("Expires At", provider.expiresAt, "dateTime")}
                    {renderDetailRow("Last Accessed", provider.lastAccessed, "dateTime")}
                    {renderDetailRow("API Key", provider.apiKey, "json")}
                    {renderDetailRow("Is Official Provider", provider.isOfficialProvider, "bool")}
                    {renderDetailRow("TOS Accepted", provider.tosAccepted, "bool")}
                    {renderDetailRow("TOS Accepted At", provider.tosAcceptedAt, "dateTime")}
                    {renderDetailRow(
                      "TOS Accepted By",
                      provider.tosAcceptedBy ? provider.tosAcceptedBy.username : null
                    )}
                    {renderDetailRow(
                      "RFC 1034 Compliant Name",
                      provider.rfc1034CompliantName
                    )}
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

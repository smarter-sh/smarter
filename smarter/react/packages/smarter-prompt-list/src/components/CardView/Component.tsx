/**
 * CardView React Component
 *
 * This component renders llmclient resources as individual cards, displaying detailed information and actions for each llmclient.
 * It is used to present llmclients in a card-based layout, with modals for clone, rename, and delete actions.
 *
 * Features:
 * - Displays llmclient details in a visually distinct card format.
 * - Integrates action buttons for open, edit, clone, rename, and delete operations.
 * - Uses modal dialogs for clone, rename, and delete workflows (scaffolded for further logic).
 * - Supports a custom detail row renderer for flexible display of llmclient attributes.
 * - Accepts a custom CSS class for layout control.
 *
 * Props:
 * - sessionContext (SessionContext): Authentication and API context for actions.
 * - title (string): Title displayed above the card list.
 * - llmclients (LLMClient[]): Array of llmclient objects to display.
 * - renderDetailRow (function): Function to render detail rows for llmclient attributes.
 *
 * Usage:
 * <CardView sessionContext={sessionContext} title="Your LLMClients" objects={llmclients} renderDetailRow={renderDetailRow} />
 *
 * This component is intended for use in views where objects are presented in a card/grid format.
 */
import type { SessionContext } from "@smarter/common";
import type { LLMClient } from "@/lib/Types";
import { loggerPrefix } from "@/const";
import { Toolbar } from "@/components/Toolbar";
import { StatusBar } from "@/components/StatusBar";
import { renderDetailRow } from "@/components/CardView/renderDetail";

import "./styles.css";

interface CardViewProps {
  sessionContext: SessionContext;
  objects: LLMClient[];
  onRequery: () => void;
}

export function CardView({ sessionContext, objects, onRequery }: CardViewProps) {
  console.debug(loggerPrefix, "Rendering CardView with objects:", objects, sessionContext);

  return (
    <div className="row g-4 p-4">
      {Array.isArray(objects) &&
        objects.map((llmclient) => (
          <div className="col-12" key={llmclient.id}>
            <div className="card h-100">
              <div className="card-header d-flex justify-content-between align-items-center bg-white border-bottom-0 pb-0">
                <Toolbar sessionContext={sessionContext} llmclient={llmclient} onRequery={onRequery} />
                <span className="border rounded p-2">
                  <StatusBar llmclient={llmclient} />
                </span>
              </div>
              <div className="card-body">
                <h5 className="card-title mb-3 text-primary fw-bold text-center">
                  <a href={llmclient.urlChatapp} className="text-decoration-none text-primary">
                    {llmclient.name}
                  </a>
                </h5>
                <table className="table table-bordered table-sm align-middle mb-0">
                  <tbody>
                    {renderDetailRow(
                      "Hashed ID",
                      llmclient.hashedId,
                      "string",
                      "Unique identifier for the llmclient, used in URLs and API calls",
                    )}
                    {renderDetailRow(
                      "Authentication Required",
                      llmclient.isAuthenticationRequired,
                      "bool",
                      "Indicates whether one or more active API keys are attached to this llmclient",
                    )}
                    {renderDetailRow("Status", llmclient.deployed ? "Deployed" : "Not deployed")}
                    {renderDetailRow("Ready", llmclient.ready, "bool")}
                    {renderDetailRow("Owner", llmclient.userProfile?.user?.username)}
                    {renderDetailRow("Created", llmclient.createdAt, "dateTime")}
                    {renderDetailRow("Last updated", llmclient.updatedAt, "dateTime")}
                    {renderDetailRow("Version", llmclient.version)}
                    {renderDetailRow("Description", llmclient.description)}
                    {renderDetailRow(
                      "Tags",
                      llmclient.tags,
                      "str[]",
                      "User-defined list of search tags for categorizing the llmclient.",
                    )}
                    {renderDetailRow(
                      "Annotations",
                      llmclient.annotations,
                      "json",
                      "User-defined list of key-value pairs for informational or platform extensibility purposes.",
                    )}
                    {renderDetailRow(
                      "Functions",
                      Array.isArray(llmclient.functions)
                        ? llmclient.functions
                            .map((f) => f?.name + "()" || "")
                            .filter(Boolean)
                            .join(", ")
                        : "",
                      "string",
                      "Comma-separated list of function names attached to this llmclient.",
                    )}
                    {renderDetailRow(
                      "Plugins",
                      Array.isArray(llmclient.plugins)
                        ? llmclient.plugins
                            .map((p) => p?.name || "")
                            .filter(Boolean)
                            .join(", ")
                        : "",
                      "string",
                      "Comma-separated list of plugin names attached to this llmclient.",
                    )}
                    {renderDetailRow(
                      "Custom Domains",
                      llmclient.customDomains?.length ? JSON.stringify(llmclient.customDomains) : undefined,
                    )}
                    {renderDetailRow("API Keys", llmclient.apiKeys?.length ? JSON.stringify(llmclient.apiKeys) : undefined)}
                    {renderDetailRow(
                      "RFC1034 Name",
                      llmclient.rfc1034CompliantName,
                      null,
                      "RFC 1034 compliant name derived from the llmclient name, used for subdomain generation",
                    )}
                    {renderDetailRow("Default System Role", llmclient.defaultSystemRole)}
                    {renderDetailRow("Base API Domain", llmclient.baseApiDomain)}
                    {renderDetailRow("Base Default Host", llmclient.baseDefaultHost)}
                    {renderDetailRow("Default Host", llmclient.defaultHost)}
                    {renderDetailRow("Base Default URL", llmclient.defaultUrl, "url")}
                    {renderDetailRow("Custom Host", llmclient.customHost, null, "Custom host set by the user, if any.")}
                    {renderDetailRow(
                      "Custom URL",
                      llmclient.customUrl,
                      "url",
                      "Custom domain and base URL set by the user, if any.",
                    )}
                    {renderDetailRow("Sandbox Host", llmclient.sandboxHost)}
                    {renderDetailRow("Base Sandbox URL", llmclient.sandboxUrl, "url")}
                    {renderDetailRow("Hostname", llmclient.hostname)}
                    {renderDetailRow(
                      "Base URL",
                      llmclient.url,
                      "url",
                      "Note that the base URL does not resolve to a working endpoint. Add '/chat' or '/config' to this URL.",
                    )}
                    {renderDetailRow(
                      "URL LLMClient",
                      llmclient.urlLLMClient,
                      "url",
                      "POST only endpoint for llmclient interactions.",
                    )}
                    {renderDetailRow(
                      "URL Chat Config",
                      llmclient.urlChatConfig,
                      "url",
                      "POST only endpoint for llmclient configuration retrieval.",
                    )}
                    {renderDetailRow("URL Chatapp", llmclient.urlChatapp, "url")}
                    {renderDetailRow("URL Manifest", llmclient.urlManifest, "url")}
                    {renderDetailRow("Provider", llmclient.provider)}
                    {renderDetailRow("Model", llmclient.defaultModel)}
                    {renderDetailRow("Temperature", llmclient.defaultTemperature, "number")}
                    {renderDetailRow("Max Tokens", llmclient.defaultMaxTokens, "number")}
                    {renderDetailRow("App Name", llmclient.appName)}
                    {renderDetailRow("App Assistant", llmclient.appAssistant)}
                    {renderDetailRow("App Welcome Message", llmclient.appWelcomeMessage)}
                    {renderDetailRow("App Example Prompts", llmclient.appExamplePrompts, "str[]")}
                    {renderDetailRow("App Placeholder", llmclient.appPlaceholder)}
                    {renderDetailRow("App Info URL", llmclient.appInfoUrl, "url")}
                    {renderDetailRow("App Background Image URL", llmclient.appBackgroundImageUrl, "url")}
                    {renderDetailRow("App Logo URL", llmclient.appLogoUrl, "url")}
                    {renderDetailRow("App File Attachment", llmclient.appFileAttachment, "bool")}
                    {renderDetailRow("DNS Status", llmclient.dnsVerificationStatus)}
                    {renderDetailRow("TLS Certificate Issuance Status", llmclient.tlsCertificateIssuanceStatus)}
                    {renderDetailRow("Subdomain", llmclient.subdomain)}
                    {renderDetailRow("Custom Domain", llmclient.customDomain)}
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

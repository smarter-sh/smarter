/**
 * CardView React Component
 *
 * This component renders llm_client resources as individual cards, displaying detailed information and actions for each llm_client.
 * It is used to present llm_clients in a card-based layout, with modals for clone, rename, and delete actions.
 *
 * Features:
 * - Displays llm_client details in a visually distinct card format.
 * - Integrates action buttons for open, edit, clone, rename, and delete operations.
 * - Uses modal dialogs for clone, rename, and delete workflows (scaffolded for further logic).
 * - Supports a custom detail row renderer for flexible display of llm_client attributes.
 * - Accepts a custom CSS class for layout control.
 *
 * Props:
 * - sessionContext (SessionContext): Authentication and API context for actions.
 * - title (string): Title displayed above the card list.
 * - llm_clients (LLMClient[]): Array of llm_client objects to display.
 * - renderDetailRow (function): Function to render detail rows for llm_client attributes.
 *
 * Usage:
 * <CardView sessionContext={sessionContext} title="Your LLMClients" objects={llm_clients} renderDetailRow={renderDetailRow} />
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
        objects.map((llm_client) => (
          <div className="col-12" key={llm_client.id}>
            <div className="card h-100">
              <div className="card-header d-flex justify-content-between align-items-center bg-white border-bottom-0 pb-0">
                <Toolbar sessionContext={sessionContext} llm_client={llm_client} onRequery={onRequery} />
                <span className="border rounded p-2">
                  <StatusBar llm_client={llm_client} />
                </span>
              </div>
              <div className="card-body">
                <h5 className="card-title mb-3 text-primary fw-bold text-center">
                  <a href={llm_client.urlChatapp} className="text-decoration-none text-primary">
                    {llm_client.name}
                  </a>
                </h5>
                <table className="table table-bordered table-sm align-middle mb-0">
                  <tbody>
                    {renderDetailRow(
                      "Hashed ID",
                      llm_client.hashedId,
                      "string",
                      "Unique identifier for the llm_client, used in URLs and API calls",
                    )}
                    {renderDetailRow(
                      "Authentication Required",
                      llm_client.isAuthenticationRequired,
                      "bool",
                      "Indicates whether one or more active API keys are attached to this llm_client",
                    )}
                    {renderDetailRow("Status", llm_client.deployed ? "Deployed" : "Not deployed")}
                    {renderDetailRow("Ready", llm_client.ready, "bool")}
                    {renderDetailRow("Owner", llm_client.userProfile?.user?.username)}
                    {renderDetailRow("Created", llm_client.createdAt, "dateTime")}
                    {renderDetailRow("Last updated", llm_client.updatedAt, "dateTime")}
                    {renderDetailRow("Version", llm_client.version)}
                    {renderDetailRow("Description", llm_client.description)}
                    {renderDetailRow(
                      "Tags",
                      llm_client.tags,
                      "str[]",
                      "User-defined list of search tags for categorizing the llm_client.",
                    )}
                    {renderDetailRow(
                      "Annotations",
                      llm_client.annotations,
                      "json",
                      "User-defined list of key-value pairs for informational or platform extensibility purposes.",
                    )}
                    {renderDetailRow(
                      "Functions",
                      Array.isArray(llm_client.functions)
                        ? llm_client.functions
                            .map((f) => f?.name + "()" || "")
                            .filter(Boolean)
                            .join(", ")
                        : "",
                      "string",
                      "Comma-separated list of function names attached to this llm_client.",
                    )}
                    {renderDetailRow(
                      "Plugins",
                      Array.isArray(llm_client.plugins)
                        ? llm_client.plugins
                            .map((p) => p?.name || "")
                            .filter(Boolean)
                            .join(", ")
                        : "",
                      "string",
                      "Comma-separated list of plugin names attached to this llm_client.",
                    )}
                    {renderDetailRow(
                      "Custom Domains",
                      llm_client.customDomains?.length ? JSON.stringify(llm_client.customDomains) : undefined,
                    )}
                    {renderDetailRow("API Keys", llm_client.apiKeys?.length ? JSON.stringify(llm_client.apiKeys) : undefined)}
                    {renderDetailRow(
                      "RFC1034 Name",
                      llm_client.rfc1034CompliantName,
                      null,
                      "RFC 1034 compliant name derived from the llm_client name, used for subdomain generation",
                    )}
                    {renderDetailRow("Default System Role", llm_client.defaultSystemRole)}
                    {renderDetailRow("Base API Domain", llm_client.baseApiDomain)}
                    {renderDetailRow("Base Default Host", llm_client.baseDefaultHost)}
                    {renderDetailRow("Default Host", llm_client.defaultHost)}
                    {renderDetailRow("Base Default URL", llm_client.defaultUrl, "url")}
                    {renderDetailRow("Custom Host", llm_client.customHost, null, "Custom host set by the user, if any.")}
                    {renderDetailRow(
                      "Custom URL",
                      llm_client.customUrl,
                      "url",
                      "Custom domain and base URL set by the user, if any.",
                    )}
                    {renderDetailRow("Sandbox Host", llm_client.sandboxHost)}
                    {renderDetailRow("Base Sandbox URL", llm_client.sandboxUrl, "url")}
                    {renderDetailRow("Hostname", llm_client.hostname)}
                    {renderDetailRow(
                      "Base URL",
                      llm_client.url,
                      "url",
                      "Note that the base URL does not resolve to a working endpoint. Add '/chat' or '/config' to this URL.",
                    )}
                    {renderDetailRow(
                      "URL LLMClient",
                      llm_client.urlLLMClient,
                      "url",
                      "POST only endpoint for llm_client interactions.",
                    )}
                    {renderDetailRow(
                      "URL Chat Config",
                      llm_client.urlChatConfig,
                      "url",
                      "POST only endpoint for llm_client configuration retrieval.",
                    )}
                    {renderDetailRow("URL Chatapp", llm_client.urlChatapp, "url")}
                    {renderDetailRow("URL Manifest", llm_client.urlManifest, "url")}
                    {renderDetailRow("Provider", llm_client.provider)}
                    {renderDetailRow("Model", llm_client.defaultModel)}
                    {renderDetailRow("Temperature", llm_client.defaultTemperature, "number")}
                    {renderDetailRow("Max Tokens", llm_client.defaultMaxTokens, "number")}
                    {renderDetailRow("App Name", llm_client.appName)}
                    {renderDetailRow("App Assistant", llm_client.appAssistant)}
                    {renderDetailRow("App Welcome Message", llm_client.appWelcomeMessage)}
                    {renderDetailRow("App Example Prompts", llm_client.appExamplePrompts, "str[]")}
                    {renderDetailRow("App Placeholder", llm_client.appPlaceholder)}
                    {renderDetailRow("App Info URL", llm_client.appInfoUrl, "url")}
                    {renderDetailRow("App Background Image URL", llm_client.appBackgroundImageUrl, "url")}
                    {renderDetailRow("App Logo URL", llm_client.appLogoUrl, "url")}
                    {renderDetailRow("App File Attachment", llm_client.appFileAttachment, "bool")}
                    {renderDetailRow("DNS Status", llm_client.dnsVerificationStatus)}
                    {renderDetailRow("TLS Certificate Issuance Status", llm_client.tlsCertificateIssuanceStatus)}
                    {renderDetailRow("Subdomain", llm_client.subdomain)}
                    {renderDetailRow("Custom Domain", llm_client.customDomain)}
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

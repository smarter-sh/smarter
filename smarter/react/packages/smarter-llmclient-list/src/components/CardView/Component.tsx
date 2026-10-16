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

import "@/components/CardView/styles.css";
import { gettext } from "@smarter/common";

/** A comma-separated list of the names of an llmclient's plugins, MCPClients or guardrails. */
const names = (items?: Array<{ name: string }>) =>
  Array.isArray(items)
    ? items
        .map((item) => item?.name || "")
        .filter(Boolean)
        .join(", ")
    : "";

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
                      gettext("Hashed ID"),
                      llmclient.hashedId,
                      "string",
                      gettext("Unique identifier for the llmclient, used in URLs and API calls"),
                    )}
                    {renderDetailRow(
                      gettext("Authentication Required"),
                      llmclient.isAuthenticationRequired,
                      "bool",
                      gettext("Indicates whether one or more active API keys are attached to this llmclient"),
                    )}
                    {renderDetailRow(
                      gettext("Status"),
                      llmclient.deployed ? gettext("Deployed") : gettext("Not deployed"),
                    )}
                    {renderDetailRow(gettext("Ready"), llmclient.ready, "bool")}
                    {renderDetailRow(gettext("Owner"), llmclient.userProfile?.user?.username)}
                    {renderDetailRow(
                      gettext("Can Delete"),
                      llmclient.canDelete,
                      "bool",
                      gettext("False if other resources depend on this llmclient, or you may not delete it."),
                    )}
                    {renderDetailRow(gettext("Created"), llmclient.createdAt, "dateTime")}
                    {renderDetailRow(gettext("Last updated"), llmclient.updatedAt, "dateTime")}
                    {renderDetailRow(gettext("Version"), llmclient.version)}
                    {renderDetailRow(gettext("Description"), llmclient.description)}
                    {renderDetailRow(
                      gettext("Tags"),
                      llmclient.tags,
                      "str[]",
                      gettext("User-defined list of search tags for categorizing the llmclient."),
                    )}
                    {renderDetailRow(
                      gettext("Annotations"),
                      llmclient.annotations,
                      "json",
                      gettext(
                        "User-defined list of key-value pairs for informational or platform extensibility purposes.",
                      ),
                    )}
                    {renderDetailRow(
                      gettext("Functions"),
                      Array.isArray(llmclient.functions)
                        ? llmclient.functions
                            .map((f) => f?.name + "()" || "")
                            .filter(Boolean)
                            .join(", ")
                        : "",
                      "string",
                      gettext("Comma-separated list of function names attached to this llmclient."),
                    )}
                    {renderDetailRow(
                      gettext("Plugins"),
                      names(llmclient.plugins),
                      "string",
                      gettext("Comma-separated list of plugin names attached to this llmclient."),
                    )}
                    {renderDetailRow(
                      gettext("MCP Clients"),
                      names(llmclient.mcpclients),
                      "string",
                      gettext(
                        "Comma-separated list of the MCPClients whose MCP servers' tools this llmclient offers the LLM.",
                      ),
                    )}
                    {renderDetailRow(
                      gettext("Guardrails"),
                      names(llmclient.guardrails),
                      "string",
                      gettext(
                        "Comma-separated list of the guardrails that check this llmclient's prompts and replies.",
                      ),
                    )}
                    {renderDetailRow(
                      gettext("Custom Domains"),
                      llmclient.customDomains?.length ? JSON.stringify(llmclient.customDomains) : undefined,
                    )}
                    {renderDetailRow(
                      gettext("API Keys"),
                      llmclient.apiKeys?.length ? JSON.stringify(llmclient.apiKeys) : undefined,
                    )}
                    {renderDetailRow(
                      gettext("RFC1034 Name"),
                      llmclient.rfc1034CompliantName,
                      null,
                      gettext("RFC 1034 compliant name derived from the llmclient name, used for subdomain generation"),
                    )}
                    {renderDetailRow(gettext("Default System Role"), llmclient.defaultSystemRole)}
                    {renderDetailRow(gettext("Base API Domain"), llmclient.baseApiDomain)}
                    {renderDetailRow(gettext("Base Default Host"), llmclient.baseDefaultHost)}
                    {renderDetailRow(gettext("Default Host"), llmclient.defaultHost)}
                    {renderDetailRow(gettext("Base Default URL"), llmclient.defaultUrl, "url")}
                    {renderDetailRow(
                      gettext("Custom Host"),
                      llmclient.customHost,
                      null,
                      gettext("Custom host set by the user, if any."),
                    )}
                    {renderDetailRow(
                      gettext("Custom URL"),
                      llmclient.customUrl,
                      "url",
                      gettext("Custom domain and base URL set by the user, if any."),
                    )}
                    {renderDetailRow(gettext("Sandbox Host"), llmclient.sandboxHost)}
                    {renderDetailRow(gettext("Base Sandbox URL"), llmclient.sandboxUrl, "url")}
                    {renderDetailRow(gettext("Hostname"), llmclient.hostname)}
                    {renderDetailRow(
                      gettext("Base URL"),
                      llmclient.url,
                      "url",
                      gettext(
                        "Note that the base URL does not resolve to a working endpoint. Add '/chat' or '/config' to this URL.",
                      ),
                    )}
                    {renderDetailRow(
                      gettext("URL LLMClient"),
                      llmclient.urlLlmclient,
                      "url",
                      gettext("POST only endpoint for llmclient interactions."),
                    )}
                    {renderDetailRow(
                      gettext("URL Chat Config"),
                      llmclient.urlChatConfig,
                      "url",
                      gettext("POST only endpoint for llmclient configuration retrieval."),
                    )}
                    {renderDetailRow(gettext("URL Chatapp"), llmclient.urlChatapp, "url")}
                    {renderDetailRow(gettext("Manifest URL"), llmclient.manifestUrl, "url")}
                    {renderDetailRow(gettext("Provider"), llmclient.provider)}
                    {renderDetailRow(gettext("Model"), llmclient.defaultModel)}
                    {renderDetailRow(gettext("Temperature"), llmclient.defaultTemperature, "number")}
                    {renderDetailRow(gettext("Max Tokens"), llmclient.defaultMaxTokens, "number")}
                    {renderDetailRow(gettext("App Name"), llmclient.appName)}
                    {renderDetailRow(gettext("App Assistant"), llmclient.appAssistant)}
                    {renderDetailRow(gettext("App Welcome Message"), llmclient.appWelcomeMessage)}
                    {renderDetailRow(gettext("App Example Prompts"), llmclient.appExamplePrompts, "str[]")}
                    {renderDetailRow(gettext("App Placeholder"), llmclient.appPlaceholder)}
                    {renderDetailRow(gettext("App Info URL"), llmclient.appInfoUrl, "url")}
                    {renderDetailRow(
                      gettext("App Background Image URL"),
                      llmclient.styles?.appBackgroundImageUrl ?? null,
                      "url",
                    )}
                    {renderDetailRow(gettext("App Logo URL"), llmclient.styles?.appLogoUrl ?? null, "url")}
                    {renderDetailRow(gettext("App File Attachment"), llmclient.appFileAttachment, "bool")}
                    {renderDetailRow(
                      gettext("Styles"),
                      llmclient.styles,
                      "json",
                      gettext("The look of the llmclient's chat: its manifest's spec.config.styles."),
                    )}
                    {renderDetailRow(
                      gettext("Allowed Origins"),
                      llmclient.allowedOrigins?.length ? llmclient.allowedOrigins : null,
                      "str[]",
                      gettext(
                        "The web origins, besides the llmclient's own hosts, that may call its api from a browser (CORS).",
                      ),
                    )}
                    {renderDetailRow(gettext("DNS Status"), llmclient.dnsVerificationStatus)}
                    {renderDetailRow(
                      gettext("TLS Certificate Issuance Status"),
                      llmclient.tlsCertificateIssuanceStatus,
                    )}
                    {renderDetailRow(gettext("Subdomain"), llmclient.subdomain)}
                    {renderDetailRow(gettext("Custom Domain"), llmclient.customDomain)}
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

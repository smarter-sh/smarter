/**
 * CardView React Component
 *
 * This component renders chatbot resources as individual cards, displaying detailed information and actions for each chatbot.
 * It is used to present chatbots in a card-based layout, with modals for clone, rename, and delete actions.
 *
 * Features:
 * - Displays chatbot details in a visually distinct card format.
 * - Integrates action buttons for open, edit, clone, rename, and delete operations.
 * - Uses modal dialogs for clone, rename, and delete workflows (scaffolded for further logic).
 * - Supports a custom detail row renderer for flexible display of chatbot attributes.
 * - Accepts a custom CSS class for layout control.
 *
 * Props:
 * - sessionContext (SessionContext): Authentication and API context for actions.
 * - title (string): Title displayed above the card list.
 * - chatbots (Chatbot[]): Array of chatbot objects to display.
 * - renderDetailRow (function): Function to render detail rows for chatbot attributes.
 *
 * Usage:
 * <CardView sessionContext={sessionContext} title="Your Chatbots" chatbots={chatbots} renderDetailRow={renderDetailRow} />
 *
 * This component is intended for use in views where chatbots are presented in a card/grid format.
 */
import type { Chatbot, SessionContext } from "@/lib/Types";
import { Toolbar } from "@/components/Toolbar";
import { StatusBar } from "@/components/StatusBar";
import { renderDetailRow } from "@/components/CardView/renderDetail";

import "./styles.css";


interface CardViewProps {
  sessionContext: SessionContext;
  chatbots: Chatbot[];
  onRequery: () => void;
}

export function CardView({ sessionContext, chatbots, onRequery }: CardViewProps) {
  console.log("Rendering CardView with chatbots:", chatbots, sessionContext);

  return (
    <div className="row g-4 p-4">
      {Array.isArray(chatbots) &&
        chatbots.map((chatbot) => (
          <div className="col-12" key={chatbot.id}>
            <div className="card h-100">
              <div className="card-header d-flex justify-content-between align-items-center bg-white border-bottom-0 pb-0">
                <Toolbar sessionContext={sessionContext} chatbot={chatbot} onRequery={onRequery} />
                <span className="border rounded p-2">
                  <StatusBar chatbot={chatbot}  />
                </span>
              </div>
              <div className="card-body">
                <h5 className="card-title mb-3 text-primary fw-bold text-center">
                  <a href={chatbot.urlChatapp} className="text-decoration-none text-primary">{chatbot.name}</a>
                </h5>
                <table className="table table-bordered table-sm align-middle mb-0">
                  <tbody>
                    {renderDetailRow("Hashed ID", chatbot.hashedId, "string", "Unique identifier for the chatbot, used in URLs and API calls")}
                    {renderDetailRow("Authentication Required", chatbot.isAuthenticationRequired, "bool", "Indicates whether one or more active API keys are attached to this chatbot")}
                    {renderDetailRow("Status", chatbot.deployed ? "Deployed" : "Not deployed")}
                    {renderDetailRow("Ready", chatbot.ready, "bool")}
                    {renderDetailRow("Owner", chatbot.userProfile?.user?.username)}
                    {renderDetailRow("Created", chatbot.createdAt, "dateTime")}
                    {renderDetailRow("Last updated", chatbot.updatedAt, "dateTime")}
                    {renderDetailRow("Version", chatbot.version)}
                    {renderDetailRow("Description", chatbot.description)}
                    {renderDetailRow("Tags", chatbot.tags, "str[]", "User-defined list of search tags for categorizing the chatbot.")}
                    {renderDetailRow("Annotations", chatbot.annotations, "json", "User-defined list of key-value pairs for informational or platform extensibility purposes.")}
                    {renderDetailRow(
                      "Functions",
                      Array.isArray(chatbot.functions)
                        ? chatbot.functions.map(f => f?.name + "()" || "").filter(Boolean).join(", ")
                        : "",
                      "string",
                      "Comma-separated list of function names attached to this chatbot."
                    )}
                    {renderDetailRow(
                      "Plugins",
                      Array.isArray(chatbot.plugins)
                        ? chatbot.plugins.map(p => p?.name || "").filter(Boolean).join(", ")
                        : "",
                      "string",
                      "Comma-separated list of plugin names attached to this chatbot."
                    )}
                    {renderDetailRow("Custom Domains", chatbot.customDomains?.length ? JSON.stringify(chatbot.customDomains) : undefined)}
                    {renderDetailRow("API Keys", chatbot.apiKeys?.length ? JSON.stringify(chatbot.apiKeys) : undefined)}
                    {renderDetailRow("RFC1034 Name", chatbot.rfc1034CompliantName, null, "RFC 1034 compliant name derived from the chatbot name, used for subdomain generation")}
                    {renderDetailRow("Default System Role", chatbot.defaultSystemRole)}
                    {renderDetailRow("Base API Domain", chatbot.baseApiDomain)}
                    {renderDetailRow("Base Default Host", chatbot.baseDefaultHost)}
                    {renderDetailRow("Default Host", chatbot.defaultHost)}
                    {renderDetailRow("Base Default URL", chatbot.defaultUrl, "url")}
                    {renderDetailRow("Custom Host", chatbot.customHost, null, "Custom host set by the user, if any.")}
                    {renderDetailRow("Custom URL", chatbot.customUrl, "url", "Custom domain and base URL set by the user, if any.")}
                    {renderDetailRow("Sandbox Host", chatbot.sandboxHost)}
                    {renderDetailRow("Base Sandbox URL", chatbot.sandboxUrl, "url")}
                    {renderDetailRow("Hostname", chatbot.hostname)}
                    {renderDetailRow("Base URL", chatbot.url, "url", "Note that the base URL does not resolve to a working endpoint. Add '/chat' or '/config' to this URL.")}
                    {renderDetailRow("URL Chatbot", chatbot.urlChatbot, "url", "POST only endpoint for chatbot interactions.")}
                    {renderDetailRow("URL Chat Config", chatbot.urlChatConfig, "url", "POST only endpoint for chatbot configuration retrieval.")}
                    {renderDetailRow("URL Chatapp", chatbot.urlChatapp, "url")}
                    {renderDetailRow("URL Manifest", chatbot.urlManifest, "url")}
                    {renderDetailRow("Provider", chatbot.provider)}
                    {renderDetailRow("Model", chatbot.defaultModel)}
                    {renderDetailRow("Temperature", chatbot.defaultTemperature, "number")}
                    {renderDetailRow("Max Tokens", chatbot.defaultMaxTokens, "number")}
                    {renderDetailRow("App Name", chatbot.appName)}
                    {renderDetailRow("App Assistant", chatbot.appAssistant)}
                    {renderDetailRow("App Welcome Message", chatbot.appWelcomeMessage)}
                    {renderDetailRow("App Example Prompts", chatbot.appExamplePrompts, "str[]")}
                    {renderDetailRow("App Placeholder", chatbot.appPlaceholder)}
                    {renderDetailRow("App Info URL", chatbot.appInfoUrl, "url")}
                    {renderDetailRow("App Background Image URL", chatbot.appBackgroundImageUrl, "url")}
                    {renderDetailRow("App Logo URL", chatbot.appLogoUrl, "url")}
                    {renderDetailRow("App File Attachment", chatbot.appFileAttachment, "bool")}
                    {renderDetailRow("DNS Status", chatbot.dnsVerificationStatus)}
                    {renderDetailRow("TLS Certificate Issuance Status", chatbot.tlsCertificateIssuanceStatus)}
                    {renderDetailRow("Subdomain", chatbot.subdomain)}
                    {renderDetailRow("Custom Domain", chatbot.customDomain)}
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

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
import type { Chatbot, SessionContext, TabKey, DetailRowRenderer } from "@/lib/Types";
import { pluginsText } from "@/lib/pluginsText";
import { Toolbar } from "@/components/Toolbar";

import "./styles.css";


interface CardViewProps {
  sessionContext: SessionContext;
  activeTab: TabKey;
  chatbots: Chatbot[];
  renderDetailRow: DetailRowRenderer;
  onRequery: () => void;
}

export function CardView({ sessionContext, activeTab, chatbots, renderDetailRow, onRequery }: CardViewProps) {
  console.log("Rendering CardView with chatbots:", chatbots, sessionContext);

  return (
    <div className="row g-4 p-4">
      {Array.isArray(chatbots) &&
        chatbots.map((chatbot) => (
          <div className="col-12" key={chatbot.id}>
            <div className="card h-100">
              <div className="card-header d-flex justify-content-between align-items-center bg-white border-bottom-0 pb-0">
                <Toolbar sessionContext={sessionContext} chatbot={chatbot} onRequery={onRequery} />
              </div>
              <div className="card-body">
                <h5 className="card-title mb-3 text-primary fw-bold text-center">
                  <a href={chatbot.urlChatapp} className="text-decoration-none text-primary">{chatbot.name}</a>
                </h5>
                <table className="table table-bordered table-sm align-middle mb-0">
                  <tbody>
                    {renderDetailRow("Hashed ID", chatbot.hashedId)}
                    {renderDetailRow("Authentication Required", chatbot.isAuthenticationRequired ? "Yes" : "No")}
                    {renderDetailRow("Status", chatbot.deployed ? "Deployed" : "Not deployed")}
                    {renderDetailRow("Ready", chatbot.ready, "bool")}
                    {renderDetailRow("Owner", chatbot.userProfile?.user?.username)}
                    {renderDetailRow("Created", chatbot.createdAt, "dateTime")}
                    {renderDetailRow("Last updated", chatbot.updatedAt, "dateTime")}
                    {renderDetailRow("Version", chatbot.version)}
                    {renderDetailRow("Description", chatbot.description)}
                    {renderDetailRow("Tags", chatbot.tags?.join(", "))}
                    {renderDetailRow("Annotations", chatbot.annotations, "json")}
                    {renderDetailRow("Functions", chatbot.functions?.length ? chatbot.functions.length : undefined)}
                    {renderDetailRow("Plugins", pluginsText(chatbot))}
                    {renderDetailRow("Custom Domains", chatbot.customDomains?.length ? JSON.stringify(chatbot.customDomains) : undefined)}
                    {renderDetailRow("API Keys", chatbot.apiKeys?.length ? JSON.stringify(chatbot.apiKeys) : undefined)}
                    {renderDetailRow("RFC1034 Name", chatbot.rfc1034CompliantName)}
                    {renderDetailRow("Default System Role", chatbot.defaultSystemRole)}
                    {renderDetailRow("Base API Domain", chatbot.baseApiDomain)}
                    {renderDetailRow("Base Default Host", chatbot.baseDefaultHost)}
                    {renderDetailRow("Default Host", chatbot.defaultHost)}
                    {renderDetailRow("Default URL", chatbot.defaultUrl, "url")}
                    {renderDetailRow("Custom Host", chatbot.customHost)}
                    {renderDetailRow("Custom URL", chatbot.customUrl, "url")}
                    {renderDetailRow("Sandbox Host", chatbot.sandboxHost)}
                    {renderDetailRow("Sandbox URL", chatbot.sandboxUrl, "url")}
                    {renderDetailRow("Hostname", chatbot.hostname)}
                    {renderDetailRow("URL", chatbot.url, "url")}
                    {renderDetailRow("URL Chatbot", chatbot.urlChatbot, "url")}
                    {renderDetailRow("URL Chat Config", chatbot.urlChatConfig, "url")}
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
                    {renderDetailRow("App File Attachment", chatbot.appFileAttachment ? "Yes" : "No")}
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

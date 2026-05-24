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
import type { ReactNode } from "react";

import type { Chatbot, SessionContext, TabKey } from "@/lib/Types";
import { formatDateTime } from "@/lib/formatDateTime";
import { pluginsText } from "@/lib/pluginsText";
import { Toolbar } from "@/components/Toolbar";

import "./styles.css";

type DetailRowRenderer = (label: string, value: string | number | null | undefined) => ReactNode;

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
    <div className="">
      {Array.isArray(chatbots) &&
        chatbots.map((chatbot) => (
          <article className="col-12 mt-1 p-2" key={chatbot.id}>
            <div
              className={`card card-flush h-xl-100 chatbot-card ${activeTab === "user" ? "user-chatbot-card" : "smarter-chatbot-card"}`}
            >
              <div className="p-5 prompt-list-card-header">
                <span className="prompt-list-header-icons">
                  {chatbot.isAuthenticationRequired ? (
                    <i className="fas fa-lock prompt-list-icon-lock" aria-label="Authentication required" />
                  ) : (
                    <i className="fas fa-unlock prompt-list-icon-unlock" aria-label="No authentication required" />
                  )}
                  {chatbot.deployed ? (
                    <i className="fas fa-check prompt-list-icon-deployed" aria-label="Deployed" />
                  ) : null}
                </span>
                <h4 className="card-title card-label fw-bold text-gray-800 text-center prompt-list-card-title">
                  <a href={chatbot.urlChatapp} className="prompt-list-card-link">
                    {chatbot.name}
                    {chatbot.version ? ` v${chatbot.version}` : ""}
                  </a>
                </h4>
              </div>
              <div className="card-body py-2">
                <table className="prompt-list-details-table">
                  <tbody>
                    {renderDetailRow("Owner", chatbot.userProfile?.user?.username)}
                    {renderDetailRow("Created", formatDateTime(chatbot.createdAt, "date"))}
                    {renderDetailRow("Last updated", formatDateTime(chatbot.updatedAt, "relative", chatbot.createdAt))}
                    {renderDetailRow("URL", chatbot.urlChatbot || chatbot.urlChatapp)}
                    {renderDetailRow("Provider", chatbot.provider)}
                    {renderDetailRow("Model", chatbot.defaultModel)}
                    {renderDetailRow("Temperature", chatbot.defaultTemperature)}
                    {renderDetailRow("Max Tokens", chatbot.defaultMaxTokens)}
                    {renderDetailRow("System Role", chatbot.defaultSystemRole)}
                    {renderDetailRow("Description", chatbot.description)}
                    {renderDetailRow("DNS status", chatbot.dnsVerificationStatus)}
                    {renderDetailRow("App assistant", chatbot.appAssistant)}
                    {renderDetailRow("App name", chatbot.appName)}
                    {renderDetailRow("Plugins", pluginsText(chatbot))}
                  </tbody>
                </table>
                <Toolbar sessionContext={sessionContext} chatbot={chatbot} onRequery={onRequery} />
              </div>
            </div>
          </article>
        ))}
    </div>
  );
}

export default CardView;

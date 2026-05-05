import type { ReactNode } from "react";

import type { Chatbot } from "@/lib/Types";
import { formatDateTime } from "@/lib/formatDateTime";
import { pluginsText } from "@/lib/pluginsText";

import "./styles.css";

type DetailRowRenderer = (
  label: string,
  value: string | number | null | undefined,
) => ReactNode;

interface CardViewProps {
  title: string;
  chatbots: Chatbot[];
  cardClassName: string;
  renderDetailRow: DetailRowRenderer;
}

export function CardView({
  title,
  chatbots,
  cardClassName,
  renderDetailRow,
}: CardViewProps) {
  return (
    <div className={cardClassName}>
      <div className="prompt-list-heading-wrap">
        <h3 className="text-center">{title}</h3>
      </div>
      {chatbots.map((chatbot) => (
        <article className="col-12 mt-1 p-2" key={chatbot.id}>
          <div
            className={`card card-flush h-xl-100 chatbot-card ${title === "Your Chatbots" ? "user-chatbot-card" : "smarter-chatbot-card"}`}
          >
            <div className="p-5 prompt-list-card-header">
              <span className="prompt-list-header-icons">
                {chatbot.isAuthenticationRequired ? (
                  <i
                    className="fas fa-lock prompt-list-icon-lock"
                    aria-label="Authentication required"
                  />
                ) : (
                  <i
                    className="fas fa-unlock prompt-list-icon-unlock"
                    aria-label="No authentication required"
                  />
                )}
                {chatbot.deployed ? (
                  <i
                    className="fas fa-check prompt-list-icon-deployed"
                    aria-label="Deployed"
                  />
                ) : null}
              </span>
              <h4 className="card-title card-label fw-bold text-gray-800 text-center prompt-list-card-title">
                <a href={chatbot.urls.chat} className="prompt-list-card-link">
                  {chatbot.name}
                  {chatbot.version ? ` v${chatbot.version}` : ""}
                </a>
              </h4>
            </div>
            <div className="card-body py-2">
              <table className="prompt-list-details-table">
                <tbody>
                  {renderDetailRow(
                    "Owner",
                    chatbot.userProfile?.user?.username,
                  )}
                  {renderDetailRow(
                    "Created",
                    formatDateTime(chatbot.createdAt),
                  )}
                  {renderDetailRow(
                    "Last updated",
                    formatDateTime(chatbot.updatedAt),
                  )}
                  {renderDetailRow(
                    "URL",
                    chatbot.urlChatbot || chatbot.urls.chat,
                  )}
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
              <div className="prompt-list-card-actions">
                <a href={chatbot.urls.chat} className="btn btn-sm btn-primary">
                  Open
                </a>
                <a href={chatbot.urls.manifest} className="btn btn-sm btn-info">
                  Manifest
                </a>
              </div>
            </div>
          </div>
        </article>
      ))}
    </div>
  );
}

export default CardView;

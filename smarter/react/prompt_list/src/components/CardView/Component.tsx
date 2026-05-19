import { useState } from "react";
import type { ReactNode } from "react";

import type { Chatbot } from "@/lib/Types";
import { formatDateTime } from "@/lib/formatDateTime";
import { pluginsText } from "@/lib/pluginsText";
import { Modal } from "@/lib/modalDialogue";

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
  // Modal state for actions
  const [modal, setModal] = useState<{
    type: null | "clone" | "rename" | "delete";
    chatbot: Chatbot | null;
  }>({ type: null, chatbot: null });

  // Handlers for new actions
  const handleClone = (chatbot: Chatbot) =>
    setModal({ type: "clone", chatbot });
  const handleRename = (chatbot: Chatbot) =>
    setModal({ type: "rename", chatbot });
  const handleDelete = (chatbot: Chatbot) =>
    setModal({ type: "delete", chatbot });
  const handleCloseModal = () => setModal({ type: null, chatbot: null });

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
                    formatDateTime(chatbot.createdAt, "date"),
                  )}
                  {renderDetailRow(
                    "Last updated",
                    formatDateTime(
                      chatbot.updatedAt,
                      "relative",
                      chatbot.createdAt,
                    ),
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
                <div
                  className="btn-group pe-2"
                  role="group"
                  aria-label="Actions"
                >
                  <a
                    href={chatbot.urls.chat}
                    className="btn btn-sm btn-primary"
                    title="Chat: Open the prompt workbench"
                    tabIndex={0}
                  >
                    <i className="bi bi-chat-dots"> Chat</i>
                  </a>
                  <a
                    href={chatbot.urls.manifest}
                    className="btn btn-sm btn-info"
                    title="Edit: Open the YAML manifest that defines this chatbot resource"
                    tabIndex={0}
                  >
                    <i className="bi bi-pencil-square"> Edit</i>
                  </a>
                  <button
                    type="button"
                    className="btn btn-sm btn-dark"
                    title="Clone: Clone this chatbot resource to a new resource owned by you"
                    onClick={() => handleClone(chatbot)}
                    tabIndex={0}
                  >
                    <i className="bi bi-files"> Clone</i>
                  </button>
                  <button
                    type="button"
                    className="btn btn-sm btn-warning"
                    title="Rename: Rename this chatbot resource"
                    onClick={() => handleRename(chatbot)}
                    tabIndex={0}
                  >
                    <i className="bi bi-pencil"> Rename</i>
                  </button>
                  <button
                    type="button"
                    className="btn btn-sm btn-danger"
                    title="Delete: Delete this chatbot resource"
                    onClick={() => handleDelete(chatbot)}
                    tabIndex={0}
                  >
                    <i className="bi bi-trash"> Delete</i>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </article>
      ))}

      {/* Modal Dialogs for Clone, Rename, Delete */}
      <Modal
        show={modal.type === "clone"}
        onClose={handleCloseModal}
        title="Clone Chatbot"
      >
        <p>
          Clone chatbot <strong>{modal.chatbot?.name}</strong> to a new resource
          owned by you.
        </p>
        <p>
          <em>Scaffold: Implement clone logic here.</em>
        </p>
      </Modal>
      <Modal
        show={modal.type === "rename"}
        onClose={handleCloseModal}
        title="Rename Chatbot"
      >
        <p>
          Rename chatbot <strong>{modal.chatbot?.name}</strong>.
        </p>
        <p>
          <em>Scaffold: Implement rename logic here.</em>
        </p>
      </Modal>
      <Modal
        show={modal.type === "delete"}
        onClose={handleCloseModal}
        title="Delete Chatbot"
      >
        <p>
          Are you sure you want to delete chatbot{" "}
          <strong>{modal.chatbot?.name}</strong>?
        </p>
        <p>
          <em>Scaffold: Implement delete logic here.</em>
        </p>
      </Modal>
    </div>
  );
}

export default CardView;

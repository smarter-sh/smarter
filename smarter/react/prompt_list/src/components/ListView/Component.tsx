import { useState } from "react";
import type { Chatbot } from "@/lib/Types";
import { pluginsText } from "@/lib/pluginsText";
import { statusCell } from "@/lib/statusCell";
import { formatDateTime } from "@/lib/formatDateTime";
import { Modal } from "@/lib/modalDialogue";
import "./styles.css";

interface ListViewProps {
  title: string;
  chatbots: Chatbot[];
  cardClassName: string;
}

export function ListView({ title, chatbots, cardClassName }: ListViewProps) {
  // Modal state
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
      <div className="table-responsive prompt-list-table-wrap">
        <table className="table table-striped table-hover align-middle">
          <thead className="table-light">
            <tr>
              <th className="p-3">Name</th>
              <th className="width-100">Created</th>
              <th className="width-100">Updated</th>
              <th>Provider</th>
              <th className="min-width-150">Model</th>
              <th>Plugins</th>
              <th>Status</th>
              <th className="text-end min-width-250"></th>
            </tr>
          </thead>
          <tbody>
            {chatbots.map((chatbot) => (
              <tr key={chatbot.id}>
                <td className="name-col p-3">
                  <a href={chatbot.urls.chat}>
                    {chatbot.name}
                    {chatbot.version ? ` v${chatbot.version}` : ""}
                  </a>
                </td>
                <td className="width-100">
                  {formatDateTime(chatbot.createdAt, "date")}
                </td>
                <td className="width-100">
                  {formatDateTime(
                    chatbot.updatedAt,
                    "relative",
                    chatbot.createdAt,
                  )}
                </td>
                <td>
                  {chatbot.appLogoUrl ? (
                    <img
                      src={chatbot.appLogoUrl}
                      alt={`${chatbot.provider} logo`}
                      className="provider-logo d-none"
                    />
                  ) : null}
                  {chatbot.provider}
                </td>
                <td className="min-width-150">
                  {chatbot.defaultModel || "default"}
                </td>
                <td>{pluginsText(chatbot)}</td>
                <td>{statusCell(chatbot)}</td>
                <td className="text-end min-width-250">
                  <div
                    className="btn-group pe-2"
                    role="group"
                    aria-label="Actions"
                  >
                    <a
                      href={chatbot.urls.chat}
                      className="btn btn-icon btn-sm btn-primary"
                      title="Chat: Open the prompt workbench"
                      tabIndex={0}
                    >
                      <i className="bi bi-chat-dots" />
                    </a>
                    <a
                      href={chatbot.urls.manifest}
                      className="btn btn-icon btn-sm btn-info"
                      title="Edit: Open the YAML manifest that defines this chatbot resource"
                      tabIndex={0}
                    >
                      <i className="bi bi-pencil-square" />
                    </a>
                    <button
                      type="button"
                      className="btn btn-icon btn-sm btn-dark"
                      title="Clone: Clone this chatbot resource to a new resource owned by you"
                      onClick={() => handleClone(chatbot)}
                      tabIndex={0}
                    >
                      <i className="bi bi-files" />
                    </button>
                    <button
                      type="button"
                      className="btn btn-icon btn-sm btn-warning"
                      title="Rename: Rename this chatbot resource"
                      onClick={() => handleRename(chatbot)}
                      tabIndex={0}
                    >
                      <i className="bi bi-pencil" />
                    </button>
                    <button
                      type="button"
                      className="btn btn-icon btn-sm btn-danger"
                      title="Delete: Delete this chatbot resource"
                      onClick={() => handleDelete(chatbot)}
                      tabIndex={0}
                    >
                      <i className="bi bi-trash" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

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

export default ListView;

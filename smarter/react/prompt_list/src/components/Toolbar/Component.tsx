import { useState } from "react";
import type { Chatbot } from "@/lib/Types";
import { Modal } from "@/lib/modalDialogue";

export const Toolbar = ({ chatbot }: { chatbot: Chatbot }) => {
  const [modal, setModal] = useState<{
    type: null | "clone" | "rename" | "delete";
    chatbot: Chatbot | null;
  }>({ type: null, chatbot: null });

  const handleCloseModal = () => setModal({ type: null, chatbot: null });

  const handleClone = (chatbot: Chatbot) =>
    setModal({ type: "clone", chatbot });
  const handleRename = (chatbot: Chatbot) =>
    setModal({ type: "rename", chatbot });
  const handleDelete = (chatbot: Chatbot) =>
    setModal({ type: "delete", chatbot });

  const ModalClone = () => {
    return (
      <>
        <Modal
          show={modal.type === "clone"}
          title="Clone Chatbot"
          onClose={handleCloseModal}
        >
          <p>
            Clone chatbot <strong>{modal.chatbot?.name}</strong> to a new
            resource owned by you.
          </p>
          <p>
            <em>Scaffold: Implement clone logic here.</em>
          </p>
        </Modal>
      </>
    );
  };

  const ModalRename = () => {
    return (
      <>
        <Modal
          show={modal.type === "rename"}
          title="Rename Chatbot"
          onClose={handleCloseModal}
        >
          <p>
            Rename chatbot <strong>{modal.chatbot?.name}</strong>.
          </p>
          <p>
            <em>Scaffold: Implement rename logic here.</em>
          </p>
        </Modal>
      </>
    );
  };

  const ModalDelete = () => {
    return (
      <>
        <Modal
          show={modal.type === "delete"}
          title="Delete Chatbot"
          onClose={handleCloseModal}
        >
          <p>
            Are you sure you want to delete chatbot{" "}
            <strong>{modal.chatbot?.name}</strong>?
          </p>
          <p>
            <em>Scaffold: Implement delete logic here.</em>
          </p>
        </Modal>
      </>
    );
  };

  return (
    <>
      <div className="btn-group pe-2" role="group" aria-label="Actions">
        <a
          href={chatbot.urls.chat}
          className="btn btn-icon btn-sm border"
          title="Chat: Open the prompt workbench"
          tabIndex={0}
        >
          <i className="bi bi-chat-dots" />
        </a>
        <a
          href={chatbot.urls.manifest}
          className="btn btn-icon btn-sm border"
          title="Edit: Open the YAML manifest that defines this chatbot resource"
          tabIndex={0}
        >
          <i className="bi bi-pencil-square" />
        </a>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Clone: Clone this chatbot resource to a new resource owned by you"
          onClick={() => handleClone(chatbot)}
          tabIndex={0}
        >
          <i className="bi bi-files" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Rename: Rename this chatbot resource"
          onClick={() => handleRename(chatbot)}
          tabIndex={0}
        >
          <i className="bi bi-pencil" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Delete: Delete this chatbot resource"
          onClick={() => handleDelete(chatbot)}
          tabIndex={0}
        >
          <i className="bi bi-trash" />
        </button>
      </div>

      <div>
        <ModalClone />
        <ModalRename />
        <ModalDelete />
      </div>
    </>
  );
};

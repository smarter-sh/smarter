/**
 * Toolbar React Component
 *
 * This component provides a toolbar for managing llmhost resources, used in both ListView and CardView displays.
 * It offers actions for opening, editing, cloning, renaming, and deleting a llmhost, with modal dialogs for confirmation and error handling.
 *
 * Features:
 * - Action buttons for: Open (chat), Edit (YAML manifest), Clone, Rename, and Delete llmhost resources.
 * - Modal dialogs for clone, rename, delete, error, and confirmation workflows.
 * - Ensures only one modal is open at a time for clear user interaction.
 * - Handles API calls for clone, rename, and delete operations, with feedback on success or failure,
 *   including the server's error message.
 * - Accessible with ARIA labels and keyboard navigation.
 *
 * The modals are defined outside of Toolbar, so that React does not recreate, and reset, them
 * each time Toolbar renders.
 *
 * Props:
 * - sessionContext (SessionContext): Contains authentication and API information for backend operations.
 * - llmhost (LLMHost): The llmhost resource to manage.
 *
 * Usage:
 * <Toolbar sessionContext={sessionContext} llmhost={llmhost} onRequery={onRequery} />
 *
 * This component is intended to be embedded in each llmhost row or card in ListView and CardView.
 */
import { useState } from "react";
import type { SessionContext } from "@smarter/common";
import { actionUrl, fetchDjangoUrl, Modal } from "@smarter/common";

import { loggerPrefix } from "@/lib/const";
import type { LLMHost } from "@/lib/Types";
import "./styles.css";

type ModalType = null | "clone" | "rename" | "delete" | "confirmation" | "error";

interface NameModalProps {
  llmhost: LLMHost | null;
  onOk: (newName: string) => void;
  onCancel: () => void;
}

/** Asks for the name of the clone. It is mounted only while open, so it starts empty. */
const ModalClone = ({ llmhost, onOk, onCancel }: NameModalProps) => {
  const [inputValue, setInputValue] = useState("");
  return (
    <Modal show title="Clone LLMHost" onOk={() => onOk(inputValue)} onCancel={onCancel}>
      <p>
        Clone llmhost <strong>{llmhost?.name}</strong> to a new resource owned by you.
      </p>
      <p>
        <em>Provide the new name for the cloned llmhost.</em>
      </p>
      <input value={inputValue} onChange={(e) => setInputValue(e.target.value)} placeholder="Enter new llmhost name" />
    </Modal>
  );
};

/** Asks for the new name. It is mounted only while open, so it starts with the current name. */
const ModalRename = ({ llmhost, onOk, onCancel }: NameModalProps) => {
  const [inputValue, setInputValue] = useState(llmhost?.name || "");
  return (
    <Modal show title="Rename LLMHost" onOk={() => onOk(inputValue)} onCancel={onCancel}>
      <p>
        Rename llmhost <strong>{llmhost?.name}</strong>.
      </p>
      <p>
        <em>Provide the new name for the llmhost.</em>
      </p>
      <input value={inputValue} onChange={(e) => setInputValue(e.target.value)} placeholder="Enter new llmhost name" />
    </Modal>
  );
};

/** Confirms the deletion. */
const ModalDelete = ({
  show,
  llmhost,
  onOk,
  onCancel,
}: {
  show: boolean;
  llmhost: LLMHost | null;
  onOk: () => void;
  onCancel: () => void;
}) => (
  <Modal show={show} title="Delete LLMHost" onOk={onOk} onCancel={onCancel}>
    <p>
      Are you sure you want to delete llmhost <strong>{llmhost?.name}</strong>?
    </p>
    <p>
      <em>Data is not recoverable.</em>
    </p>
  </Modal>
);

/** Shows the error message. */
const ModalError = ({
  show,
  llmhost,
  message,
  onClose,
}: {
  show: boolean;
  llmhost: LLMHost | null;
  message: string;
  onClose: () => void;
}) => (
  <Modal show={show} title="❌ Error" onClose={onClose}>
    <p>
      An error occurred while performing the operation on llmhost <strong>{llmhost?.name}</strong>.
    </p>
    <p>{message ? <span className="text-danger">{message}</span> : <em>An unknown error occurred.</em>}</p>
  </Modal>
);

/** Confirms that the operation succeeded. */
const ModalConfirmation = ({
  show,
  llmhost,
  message,
  onClose,
}: {
  show: boolean;
  llmhost: LLMHost | null;
  message: string;
  onClose: () => void;
}) => (
  <Modal show={show} title="✅ Success" onClose={onClose}>
    <p>
      {message} <strong>{llmhost?.name}</strong>.
    </p>
    <p>
      <em>Operation completed successfully.</em>
    </p>
  </Modal>
);

interface ToolbarProps {
  sessionContext: SessionContext;
  llmhost: LLMHost;
  onRequery: () => void;
}

export const Toolbar = ({ sessionContext, llmhost, onRequery }: ToolbarProps) => {
  // this is a single way to control which and whether a modal is open.
  // it ensures that only one modal can be open at a time.
  const [modal, setModal] = useState<{ type: ModalType; llmhost: LLMHost | null }>({ type: null, llmhost: null });
  const [errMessage, setErrMessage] = useState<string>("");
  const [successMessage, setSuccessMessage] = useState<string>("");

  const handleCloseModal = () => {
    setModal({ type: null, llmhost: null });
  };
  const handleCloseModalWithRequery = () => {
    setModal({ type: null, llmhost: null });
    onRequery();
  };

  /**
   * POST to one of the list API's actions, e.g. clone/12/new_name/, and show the result: the
   * confirmation modal on success, else the error modal with the server's error message.
   * See actionUrl() in @smarter/common for how the action's URL is built.
   */
  const runAction = (target: LLMHost, path: string, verb: "clone" | "rename" | "delete") => {
    handleCloseModal();
    fetchDjangoUrl(sessionContext, actionUrl(sessionContext, path), JSON.stringify({}))
      .then(async (response) => {
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(`Failed to ${verb} llmhost (${response.status}): ${data.error || response.statusText}`);
        }
        return data;
      })
      .then((data) => {
        console.debug(loggerPrefix, `Successfully ${verb}d llmhost:`, data);
        setSuccessMessage(`Successfully ${verb}d llmhost`);
        // clone and rename return the resulting llmhost; delete returns a message.
        setModal({ type: "confirmation", llmhost: data && data.id ? (data as LLMHost) : target });
      })
      .catch((error) => {
        console.error(loggerPrefix, `Error trying to ${verb} llmhost:`, error);
        setErrMessage(error.message);
        setModal({ type: "error", llmhost: target });
      });
  };

  return (
    <>
      <div className="toolbar btn-group pe-2" role="group" aria-label="Actions">
        <a
          href={llmhost.manifestUrl}
          className="btn btn-icon btn-sm border"
          title="Chat: Open the llmhost workbench"
          tabIndex={0}
        >
          <i className="bi bi-chat-dots md-teal" />
        </a>
        <a
          href={llmhost.manifestUrl}
          className="btn btn-icon btn-sm border"
          title="Edit: Open the YAML manifest that defines this llmhost resource"
          tabIndex={0}
        >
          <i className="bi bi-pencil-square md-blue" />
        </a>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Clone: Clone this llmhost resource to a new resource owned by you"
          onClick={() => setModal({ type: "clone", llmhost })}
          tabIndex={0}
        >
          <i className="bi bi-files md-green" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Rename: Rename this llmhost resource"
          onClick={() => setModal({ type: "rename", llmhost })}
          tabIndex={0}
        >
          <i className="bi bi-pencil md-blue" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title={
            llmhost.canDelete === false
              ? "Delete: You can't delete this llmhost, because other resources depend on it, or you don't have permission to delete it"
              : "Delete: Delete this llmhost resource"
          }
          onClick={() => setModal({ type: "delete", llmhost })}
          disabled={llmhost.canDelete === false}
          tabIndex={0}
        >
          <i className="bi bi-trash md-red" />
        </button>
      </div>

      <div>
        {modal.type === "clone" && (
          <ModalClone
            llmhost={modal.llmhost}
            onOk={(newName) => runAction(modal.llmhost!, `clone/${modal.llmhost!.id}/${newName}/`, "clone")}
            onCancel={handleCloseModal}
          />
        )}
        {modal.type === "rename" && (
          <ModalRename
            llmhost={modal.llmhost}
            onOk={(newName) => runAction(modal.llmhost!, `rename/${modal.llmhost!.id}/${newName}/`, "rename")}
            onCancel={handleCloseModal}
          />
        )}
        <ModalDelete
          show={modal.type === "delete"}
          llmhost={modal.llmhost}
          onOk={() => runAction(modal.llmhost!, `delete/${modal.llmhost!.id}/`, "delete")}
          onCancel={handleCloseModal}
        />
        <ModalError
          show={modal.type === "error"}
          llmhost={modal.llmhost}
          message={errMessage}
          onClose={handleCloseModal}
        />
        <ModalConfirmation
          show={modal.type === "confirmation"}
          llmhost={modal.llmhost}
          message={successMessage}
          onClose={handleCloseModalWithRequery}
        />
      </div>
    </>
  );
};

/**
 * Toolbar React Component
 *
 * This component provides a toolbar for managing orchestrator resources, used in both ListView and CardView displays.
 * It offers actions for opening, editing, cloning, renaming, and deleting an orchestrator, with modal dialogs for confirmation and error handling.
 *
 * Features:
 * - Action buttons for: Open (chat), Edit (YAML manifest), Clone, Rename, and Delete orchestrator resources.
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
 * - orchestrator (Orchestrator): The orchestrator resource to manage.
 *
 * Usage:
 * <Toolbar sessionContext={sessionContext} orchestrator={orchestrator} onRequery={onRequery} />
 *
 * This component is intended to be embedded in each orchestrator row or card in ListView and CardView.
 */
import { useState } from "react";
import type { SessionContext } from "@smarter/common";
import { actionUrl, fetchDjangoUrl, Modal } from "@smarter/common";

import { loggerPrefix } from "@/lib/const";
import type { Orchestrator } from "@/lib/Types";

type ModalType = null | "clone" | "rename" | "delete" | "confirmation" | "error";

interface NameModalProps {
  orchestrator: Orchestrator | null;
  onOk: (newName: string) => void;
  onCancel: () => void;
}

/** Asks for the name of the clone. It is mounted only while open, so it starts empty. */
const ModalClone = ({ orchestrator, onOk, onCancel }: NameModalProps) => {
  const [inputValue, setInputValue] = useState("");
  return (
    <Modal show title="Clone Orchestrator" onOk={() => onOk(inputValue)} onCancel={onCancel}>
      <p>
        Clone orchestrator <strong>{orchestrator?.name}</strong> to a new resource owned by you.
      </p>
      <p>
        <em>Provide the new name for the cloned orchestrator.</em>
      </p>
      <input value={inputValue} onChange={(e) => setInputValue(e.target.value)} placeholder="Enter new orchestrator name" />
    </Modal>
  );
};

/** Asks for the new name. It is mounted only while open, so it starts with the current name. */
const ModalRename = ({ orchestrator, onOk, onCancel }: NameModalProps) => {
  const [inputValue, setInputValue] = useState(orchestrator?.name || "");
  return (
    <Modal show title="Rename Orchestrator" onOk={() => onOk(inputValue)} onCancel={onCancel}>
      <p>
        Rename orchestrator <strong>{orchestrator?.name}</strong>.
      </p>
      <p>
        <em>Provide the new name for the orchestrator.</em>
      </p>
      <input value={inputValue} onChange={(e) => setInputValue(e.target.value)} placeholder="Enter new orchestrator name" />
    </Modal>
  );
};

/** Confirms the deletion. */
const ModalDelete = ({
  show,
  orchestrator,
  onOk,
  onCancel,
}: {
  show: boolean;
  orchestrator: Orchestrator | null;
  onOk: () => void;
  onCancel: () => void;
}) => (
  <Modal show={show} title="Delete Orchestrator" onOk={onOk} onCancel={onCancel}>
    <p>
      Are you sure you want to delete orchestrator <strong>{orchestrator?.name}</strong>?
    </p>
    <p>
      <em>Data is not recoverable.</em>
    </p>
  </Modal>
);

/** Shows the error message. */
const ModalError = ({
  show,
  orchestrator,
  message,
  onClose,
}: {
  show: boolean;
  orchestrator: Orchestrator | null;
  message: string;
  onClose: () => void;
}) => (
  <Modal show={show} title="❌ Error" onClose={onClose}>
    <p>
      An error occurred while performing the operation on orchestrator <strong>{orchestrator?.name}</strong>.
    </p>
    <p>{message ? <span className="text-danger">{message}</span> : <em>An unknown error occurred.</em>}</p>
  </Modal>
);

/** Confirms that the operation succeeded. */
const ModalConfirmation = ({
  show,
  orchestrator,
  message,
  onClose,
}: {
  show: boolean;
  orchestrator: Orchestrator | null;
  message: string;
  onClose: () => void;
}) => (
  <Modal show={show} title="✅ Success" onClose={onClose}>
    <p>
      {message} <strong>{orchestrator?.name}</strong>.
    </p>
    <p>
      <em>Operation completed successfully.</em>
    </p>
  </Modal>
);

interface ToolbarProps {
  sessionContext: SessionContext;
  orchestrator: Orchestrator;
  onRequery: () => void;
}

export const Toolbar = ({ sessionContext, orchestrator, onRequery }: ToolbarProps) => {
  // this is a single way to control which and whether a modal is open.
  // it ensures that only one modal can be open at a time.
  const [modal, setModal] = useState<{ type: ModalType; orchestrator: Orchestrator | null }>({ type: null, orchestrator: null });
  const [errMessage, setErrMessage] = useState<string>("");
  const [successMessage, setSuccessMessage] = useState<string>("");

  const handleCloseModal = () => {
    setModal({ type: null, orchestrator: null });
  };
  const handleCloseModalWithRequery = () => {
    setModal({ type: null, orchestrator: null });
    onRequery();
  };

  /**
   * POST to one of the list API's actions, e.g. clone/12/new_name/, and show the result: the
   * confirmation modal on success, else the error modal with the server's error message.
   * See actionUrl() in @smarter/common for how the action's URL is built.
   */
  const runAction = (target: Orchestrator, path: string, verb: "clone" | "rename" | "delete") => {
    handleCloseModal();
    fetchDjangoUrl(sessionContext, actionUrl(sessionContext, path), JSON.stringify({}))
      .then(async (response) => {
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(`Failed to ${verb} orchestrator (${response.status}): ${data.error || response.statusText}`);
        }
        return data;
      })
      .then((data) => {
        console.debug(loggerPrefix, `Successfully ${verb}d orchestrator:`, data);
        setSuccessMessage(`Successfully ${verb}d orchestrator`);
        // clone and rename return the resulting orchestrator; delete returns a message.
        setModal({ type: "confirmation", orchestrator: data && data.id ? (data as Orchestrator) : target });
      })
      .catch((error) => {
        console.error(loggerPrefix, `Error trying to ${verb} orchestrator:`, error);
        setErrMessage(error.message);
        setModal({ type: "error", orchestrator: target });
      });
  };

  return (
    <>
      <div className="toolbar btn-group pe-2" role="group" aria-label="Actions">
        <a
          href={orchestrator.manifestUrl}
          className="btn btn-icon btn-sm border"
          title="Chat: Open the orchestrator workbench"
          tabIndex={0}
        >
          <i className="bi bi-chat-dots" />
        </a>
        <a
          href={orchestrator.manifestUrl}
          className="btn btn-icon btn-sm border"
          title="Edit: Open the YAML manifest that defines this orchestrator resource"
          tabIndex={0}
        >
          <i className="bi bi-pencil-square" />
        </a>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Clone: Clone this orchestrator resource to a new resource owned by you"
          onClick={() => setModal({ type: "clone", orchestrator })}
          tabIndex={0}
        >
          <i className="bi bi-files" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Rename: Rename this orchestrator resource"
          onClick={() => setModal({ type: "rename", orchestrator })}
          tabIndex={0}
        >
          <i className="bi bi-pencil" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title={
            orchestrator.canDelete === false
              ? "Delete: You can't delete this orchestrator, because other resources depend on it, or you don't have permission to delete it"
              : "Delete: Delete this orchestrator resource"
          }
          onClick={() => setModal({ type: "delete", orchestrator })}
          disabled={orchestrator.canDelete === false}
          tabIndex={0}
        >
          <i className="bi bi-trash" />
        </button>
      </div>

      <div>
        {modal.type === "clone" && (
          <ModalClone
            orchestrator={modal.orchestrator}
            onOk={(newName) => runAction(modal.orchestrator!, `clone/${modal.orchestrator!.id}/${newName}/`, "clone")}
            onCancel={handleCloseModal}
          />
        )}
        {modal.type === "rename" && (
          <ModalRename
            orchestrator={modal.orchestrator}
            onOk={(newName) => runAction(modal.orchestrator!, `rename/${modal.orchestrator!.id}/${newName}/`, "rename")}
            onCancel={handleCloseModal}
          />
        )}
        <ModalDelete
          show={modal.type === "delete"}
          orchestrator={modal.orchestrator}
          onOk={() => runAction(modal.orchestrator!, `delete/${modal.orchestrator!.id}/`, "delete")}
          onCancel={handleCloseModal}
        />
        <ModalError show={modal.type === "error"} orchestrator={modal.orchestrator} message={errMessage} onClose={handleCloseModal} />
        <ModalConfirmation
          show={modal.type === "confirmation"}
          orchestrator={modal.orchestrator}
          message={successMessage}
          onClose={handleCloseModalWithRequery}
        />
      </div>
    </>
  );
};

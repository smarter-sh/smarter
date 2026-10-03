/**
 * Toolbar React Component
 *
 * This component provides a toolbar for managing secret resources, used in both ListView and CardView displays.
 * It offers actions for opening, editing, cloning, renaming, and deleting a secret, with modal dialogs for confirmation and error handling.
 *
 * Features:
 * - Action buttons for: Open (chat), Edit (YAML manifest), Clone, Rename, and Delete secret resources.
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
 * - secret (Secret): The secret resource to manage.
 *
 * Usage:
 * <Toolbar sessionContext={sessionContext} secret={secret} onRequery={onRequery} />
 *
 * This component is intended to be embedded in each secret row or card in ListView and CardView.
 */
import { useState } from "react";
import type { SessionContext } from "@smarter/common";
import { actionUrl, fetchDjangoUrl, Modal } from "@smarter/common";

import { loggerPrefix } from "@/lib/const";
import type { Secret } from "@/lib/Types";
import "./styles.css";

type ModalType = null | "clone" | "rename" | "delete" | "confirmation" | "error";

interface NameModalProps {
  secret: Secret | null;
  onOk: (newName: string) => void;
  onCancel: () => void;
}

/** Asks for the name of the clone. It is mounted only while open, so it starts empty. */
const ModalClone = ({ secret, onOk, onCancel }: NameModalProps) => {
  const [inputValue, setInputValue] = useState("");
  return (
    <Modal show title="Clone Secret" onOk={() => onOk(inputValue)} onCancel={onCancel}>
      <p>
        Clone secret <strong>{secret?.name}</strong> to a new resource owned by you.
      </p>
      <p>
        <em>Provide the new name for the cloned secret.</em>
      </p>
      <input value={inputValue} onChange={(e) => setInputValue(e.target.value)} placeholder="Enter new secret name" />
    </Modal>
  );
};

/** Asks for the new name. It is mounted only while open, so it starts with the current name. */
const ModalRename = ({ secret, onOk, onCancel }: NameModalProps) => {
  const [inputValue, setInputValue] = useState(secret?.name || "");
  return (
    <Modal show title="Rename Secret" onOk={() => onOk(inputValue)} onCancel={onCancel}>
      <p>
        Rename secret <strong>{secret?.name}</strong>.
      </p>
      <p>
        <em>Provide the new name for the secret.</em>
      </p>
      <input value={inputValue} onChange={(e) => setInputValue(e.target.value)} placeholder="Enter new secret name" />
    </Modal>
  );
};

/** Confirms the deletion. */
const ModalDelete = ({
  show,
  secret,
  onOk,
  onCancel,
}: {
  show: boolean;
  secret: Secret | null;
  onOk: () => void;
  onCancel: () => void;
}) => (
  <Modal show={show} title="Delete Secret" onOk={onOk} onCancel={onCancel}>
    <p>
      Are you sure you want to delete secret <strong>{secret?.name}</strong>?
    </p>
    <p>
      <em>Data is not recoverable.</em>
    </p>
  </Modal>
);

/** Shows the error message. */
const ModalError = ({
  show,
  secret,
  message,
  onClose,
}: {
  show: boolean;
  secret: Secret | null;
  message: string;
  onClose: () => void;
}) => (
  <Modal show={show} title="❌ Error" onClose={onClose}>
    <p>
      An error occurred while performing the operation on secret <strong>{secret?.name}</strong>.
    </p>
    <p>{message ? <span className="text-danger">{message}</span> : <em>An unknown error occurred.</em>}</p>
  </Modal>
);

/** Confirms that the operation succeeded. */
const ModalConfirmation = ({
  show,
  secret,
  message,
  onClose,
}: {
  show: boolean;
  secret: Secret | null;
  message: string;
  onClose: () => void;
}) => (
  <Modal show={show} title="✅ Success" onClose={onClose}>
    <p>
      {message} <strong>{secret?.name}</strong>.
    </p>
    <p>
      <em>Operation completed successfully.</em>
    </p>
  </Modal>
);

interface ToolbarProps {
  sessionContext: SessionContext;
  secret: Secret;
  onRequery: () => void;
}

export const Toolbar = ({ sessionContext, secret, onRequery }: ToolbarProps) => {
  // this is a single way to control which and whether a modal is open.
  // it ensures that only one modal can be open at a time.
  const [modal, setModal] = useState<{ type: ModalType; secret: Secret | null }>({ type: null, secret: null });
  const [errMessage, setErrMessage] = useState<string>("");
  const [successMessage, setSuccessMessage] = useState<string>("");

  const handleCloseModal = () => {
    setModal({ type: null, secret: null });
  };
  const handleCloseModalWithRequery = () => {
    setModal({ type: null, secret: null });
    onRequery();
  };

  /**
   * POST to one of the list API's actions, e.g. clone/12/new_name/, and show the result: the
   * confirmation modal on success, else the error modal with the server's error message.
   * See actionUrl() in @smarter/common for how the action's URL is built.
   */
  const runAction = (target: Secret, path: string, verb: "clone" | "rename" | "delete") => {
    handleCloseModal();
    fetchDjangoUrl(sessionContext, actionUrl(sessionContext, path), JSON.stringify({}))
      .then(async (response) => {
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(`Failed to ${verb} secret (${response.status}): ${data.error || response.statusText}`);
        }
        return data;
      })
      .then((data) => {
        console.debug(loggerPrefix, `Successfully ${verb}d secret:`, data);
        setSuccessMessage(`Successfully ${verb}d secret`);
        // clone and rename return the resulting secret; delete returns a message.
        setModal({ type: "confirmation", secret: data && data.id ? (data as Secret) : target });
      })
      .catch((error) => {
        console.error(loggerPrefix, `Error trying to ${verb} secret:`, error);
        setErrMessage(error.message);
        setModal({ type: "error", secret: target });
      });
  };

  return (
    <>
      <div className="toolbar btn-group pe-2" role="group" aria-label="Actions">
        <a
          href={secret.manifestUrl}
          className="btn btn-icon btn-sm border"
          title="Chat: Open the secret workbench"
          tabIndex={0}
        >
          <i className="bi bi-chat-dots md-teal" />
        </a>
        <a
          href={secret.manifestUrl}
          className="btn btn-icon btn-sm border"
          title="Edit: Open the YAML manifest that defines this secret resource"
          tabIndex={0}
        >
          <i className="bi bi-pencil-square md-blue" />
        </a>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Clone: Clone this secret resource to a new resource owned by you"
          onClick={() => setModal({ type: "clone", secret })}
          tabIndex={0}
        >
          <i className="bi bi-files md-green" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Rename: Rename this secret resource"
          onClick={() => setModal({ type: "rename", secret })}
          tabIndex={0}
        >
          <i className="bi bi-pencil md-blue" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title={
            secret.canDelete === false
              ? "Delete: You can't delete this secret, because other resources depend on it, or you don't have permission to delete it"
              : "Delete: Delete this secret resource"
          }
          onClick={() => setModal({ type: "delete", secret })}
          disabled={secret.canDelete === false}
          tabIndex={0}
        >
          <i className="bi bi-trash md-red" />
        </button>
      </div>

      <div>
        {modal.type === "clone" && (
          <ModalClone
            secret={modal.secret}
            onOk={(newName) => runAction(modal.secret!, `clone/${modal.secret!.id}/${newName}/`, "clone")}
            onCancel={handleCloseModal}
          />
        )}
        {modal.type === "rename" && (
          <ModalRename
            secret={modal.secret}
            onOk={(newName) => runAction(modal.secret!, `rename/${modal.secret!.id}/${newName}/`, "rename")}
            onCancel={handleCloseModal}
          />
        )}
        <ModalDelete
          show={modal.type === "delete"}
          secret={modal.secret}
          onOk={() => runAction(modal.secret!, `delete/${modal.secret!.id}/`, "delete")}
          onCancel={handleCloseModal}
        />
        <ModalError show={modal.type === "error"} secret={modal.secret} message={errMessage} onClose={handleCloseModal} />
        <ModalConfirmation
          show={modal.type === "confirmation"}
          secret={modal.secret}
          message={successMessage}
          onClose={handleCloseModalWithRequery}
        />
      </div>
    </>
  );
};

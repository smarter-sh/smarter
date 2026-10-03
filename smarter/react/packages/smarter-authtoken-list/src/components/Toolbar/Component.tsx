/**
 * Toolbar React Component
 *
 * This component provides a toolbar for managing authtoken resources, used in both ListView and CardView displays.
 * It offers actions for opening, editing, cloning, renaming, and deleting an authtoken, with modal dialogs for confirmation and error handling.
 *
 * Features:
 * - Action buttons for: Open (chat), Edit (YAML manifest), Clone, Rename, and Delete authtoken resources.
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
 * - authtoken (AuthToken): The authtoken resource to manage.
 *
 * Usage:
 * <Toolbar sessionContext={sessionContext} authtoken={authtoken} onRequery={onRequery} />
 *
 * This component is intended to be embedded in each authtoken row or card in ListView and CardView.
 */
import { useState } from "react";
import type { SessionContext } from "@smarter/common";
import { actionUrl, fetchDjangoUrl, Modal } from "@smarter/common";

import { loggerPrefix } from "@/lib/const";
import type { AuthToken } from "@/lib/Types";

type ModalType = null | "clone" | "rename" | "delete" | "confirmation" | "error";

interface NameModalProps {
  authtoken: AuthToken | null;
  onOk: (newName: string) => void;
  onCancel: () => void;
}

/** Asks for the name of the clone. It is mounted only while open, so it starts empty. */
const ModalClone = ({ authtoken, onOk, onCancel }: NameModalProps) => {
  const [inputValue, setInputValue] = useState("");
  return (
    <Modal show title="Clone AuthToken" onOk={() => onOk(inputValue)} onCancel={onCancel}>
      <p>
        Clone authtoken <strong>{authtoken?.name}</strong> to a new resource owned by you.
      </p>
      <p>
        <em>Provide the new name for the cloned authtoken.</em>
      </p>
      <input value={inputValue} onChange={(e) => setInputValue(e.target.value)} placeholder="Enter new authtoken name" />
    </Modal>
  );
};

/** Asks for the new name. It is mounted only while open, so it starts with the current name. */
const ModalRename = ({ authtoken, onOk, onCancel }: NameModalProps) => {
  const [inputValue, setInputValue] = useState(authtoken?.name || "");
  return (
    <Modal show title="Rename AuthToken" onOk={() => onOk(inputValue)} onCancel={onCancel}>
      <p>
        Rename authtoken <strong>{authtoken?.name}</strong>.
      </p>
      <p>
        <em>Provide the new name for the authtoken.</em>
      </p>
      <input value={inputValue} onChange={(e) => setInputValue(e.target.value)} placeholder="Enter new authtoken name" />
    </Modal>
  );
};

/** Confirms the deletion. */
const ModalDelete = ({
  show,
  authtoken,
  onOk,
  onCancel,
}: {
  show: boolean;
  authtoken: AuthToken | null;
  onOk: () => void;
  onCancel: () => void;
}) => (
  <Modal show={show} title="Delete AuthToken" onOk={onOk} onCancel={onCancel}>
    <p>
      Are you sure you want to delete authtoken <strong>{authtoken?.name}</strong>?
    </p>
    <p>
      <em>Data is not recoverable.</em>
    </p>
  </Modal>
);

/** Shows the error message. */
const ModalError = ({
  show,
  authtoken,
  message,
  onClose,
}: {
  show: boolean;
  authtoken: AuthToken | null;
  message: string;
  onClose: () => void;
}) => (
  <Modal show={show} title="❌ Error" onClose={onClose}>
    <p>
      An error occurred while performing the operation on authtoken <strong>{authtoken?.name}</strong>.
    </p>
    <p>{message ? <span className="text-danger">{message}</span> : <em>An unknown error occurred.</em>}</p>
  </Modal>
);

/** Confirms that the operation succeeded. */
const ModalConfirmation = ({
  show,
  authtoken,
  message,
  onClose,
}: {
  show: boolean;
  authtoken: AuthToken | null;
  message: string;
  onClose: () => void;
}) => (
  <Modal show={show} title="✅ Success" onClose={onClose}>
    <p>
      {message} <strong>{authtoken?.name}</strong>.
    </p>
    <p>
      <em>Operation completed successfully.</em>
    </p>
  </Modal>
);

interface ToolbarProps {
  sessionContext: SessionContext;
  authtoken: AuthToken;
  onRequery: () => void;
}

export const Toolbar = ({ sessionContext, authtoken, onRequery }: ToolbarProps) => {
  // this is a single way to control which and whether a modal is open.
  // it ensures that only one modal can be open at a time.
  const [modal, setModal] = useState<{ type: ModalType; authtoken: AuthToken | null }>({ type: null, authtoken: null });
  const [errMessage, setErrMessage] = useState<string>("");
  const [successMessage, setSuccessMessage] = useState<string>("");

  const handleCloseModal = () => {
    setModal({ type: null, authtoken: null });
  };
  const handleCloseModalWithRequery = () => {
    setModal({ type: null, authtoken: null });
    onRequery();
  };

  /**
   * POST to one of the list API's actions, e.g. clone/12/new_name/, and show the result: the
   * confirmation modal on success, else the error modal with the server's error message.
   * See actionUrl() in @smarter/common for how the action's URL is built.
   */
  const runAction = (target: AuthToken, path: string, verb: "clone" | "rename" | "delete") => {
    handleCloseModal();
    fetchDjangoUrl(sessionContext, actionUrl(sessionContext, path), JSON.stringify({}))
      .then(async (response) => {
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(`Failed to ${verb} authtoken (${response.status}): ${data.error || response.statusText}`);
        }
        return data;
      })
      .then((data) => {
        console.debug(loggerPrefix, `Successfully ${verb}d authtoken:`, data);
        setSuccessMessage(`Successfully ${verb}d authtoken`);
        // clone and rename return the resulting authtoken; delete returns a message.
        setModal({ type: "confirmation", authtoken: data && data.id ? (data as AuthToken) : target });
      })
      .catch((error) => {
        console.error(loggerPrefix, `Error trying to ${verb} authtoken:`, error);
        setErrMessage(error.message);
        setModal({ type: "error", authtoken: target });
      });
  };

  return (
    <>
      <div className="toolbar btn-group pe-2" role="group" aria-label="Actions">
        <a
          href={authtoken.manifestUrl}
          className="btn btn-icon btn-sm border"
          title="Chat: Open the authtoken workbench"
          tabIndex={0}
        >
          <i className="bi bi-chat-dots" />
        </a>
        <a
          href={authtoken.manifestUrl}
          className="btn btn-icon btn-sm border"
          title="Edit: Open the YAML manifest that defines this authtoken resource"
          tabIndex={0}
        >
          <i className="bi bi-pencil-square" />
        </a>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Clone: Clone this authtoken resource to a new resource owned by you"
          onClick={() => setModal({ type: "clone", authtoken })}
          tabIndex={0}
        >
          <i className="bi bi-files" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Rename: Rename this authtoken resource"
          onClick={() => setModal({ type: "rename", authtoken })}
          tabIndex={0}
        >
          <i className="bi bi-pencil" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title={
            authtoken.canDelete === false
              ? "Delete: You can't delete this authtoken, because other resources depend on it, or you don't have permission to delete it"
              : "Delete: Delete this authtoken resource"
          }
          onClick={() => setModal({ type: "delete", authtoken })}
          disabled={authtoken.canDelete === false}
          tabIndex={0}
        >
          <i className="bi bi-trash" />
        </button>
      </div>

      <div>
        {modal.type === "clone" && (
          <ModalClone
            authtoken={modal.authtoken}
            onOk={(newName) => runAction(modal.authtoken!, `clone/${modal.authtoken!.id}/${newName}/`, "clone")}
            onCancel={handleCloseModal}
          />
        )}
        {modal.type === "rename" && (
          <ModalRename
            authtoken={modal.authtoken}
            onOk={(newName) => runAction(modal.authtoken!, `rename/${modal.authtoken!.id}/${newName}/`, "rename")}
            onCancel={handleCloseModal}
          />
        )}
        <ModalDelete
          show={modal.type === "delete"}
          authtoken={modal.authtoken}
          onOk={() => runAction(modal.authtoken!, `delete/${modal.authtoken!.id}/`, "delete")}
          onCancel={handleCloseModal}
        />
        <ModalError show={modal.type === "error"} authtoken={modal.authtoken} message={errMessage} onClose={handleCloseModal} />
        <ModalConfirmation
          show={modal.type === "confirmation"}
          authtoken={modal.authtoken}
          message={successMessage}
          onClose={handleCloseModalWithRequery}
        />
      </div>
    </>
  );
};

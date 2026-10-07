/**
 * Toolbar React Component
 *
 * This component provides a toolbar for managing vectorstore resources, used in both ListView and CardView displays.
 * It offers actions for opening, editing, cloning, renaming, and deleting a vectorstore, with modal dialogs for confirmation and error handling.
 *
 * Features:
 * - Action buttons for: Open (chat), Edit (YAML manifest), Clone, Rename, and Delete vectorstore resources.
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
 * - vectorstore (Vectorstore): The vectorstore resource to manage.
 *
 * Usage:
 * <Toolbar sessionContext={sessionContext} vectorstore={vectorstore} onRequery={onRequery} />
 *
 * This component is intended to be embedded in each vectorstore row or card in ListView and CardView.
 */
import { useState } from "react";
import type { SessionContext } from "@smarter/common";
import { actionUrl, fetchDjangoUrl, Modal } from "@smarter/common";

import { loggerPrefix } from "@/lib/const";
import type { Vectorstore } from "@/lib/Types";
import "./styles.css";

type ModalType = null | "clone" | "rename" | "delete" | "confirmation" | "error";

interface NameModalProps {
  vectorstore: Vectorstore | null;
  onOk: (newName: string) => void;
  onCancel: () => void;
}

/** Asks for the name of the clone. It is mounted only while open, so it starts empty. */
const ModalClone = ({ vectorstore, onOk, onCancel }: NameModalProps) => {
  const [inputValue, setInputValue] = useState("");
  return (
    <Modal show title="Clone Vectorstore" onOk={() => onOk(inputValue)} onCancel={onCancel}>
      <p>
        Clone vectorstore <strong>{vectorstore?.name}</strong> to a new resource owned by you.
      </p>
      <p>
        <em>Provide the new name for the cloned vectorstore.</em>
      </p>
      <input
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        placeholder="Enter new vectorstore name"
      />
    </Modal>
  );
};

/** Asks for the new name. It is mounted only while open, so it starts with the current name. */
const ModalRename = ({ vectorstore, onOk, onCancel }: NameModalProps) => {
  const [inputValue, setInputValue] = useState(vectorstore?.name || "");
  return (
    <Modal show title="Rename Vectorstore" onOk={() => onOk(inputValue)} onCancel={onCancel}>
      <p>
        Rename vectorstore <strong>{vectorstore?.name}</strong>.
      </p>
      <p>
        <em>Provide the new name for the vectorstore.</em>
      </p>
      <input
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        placeholder="Enter new vectorstore name"
      />
    </Modal>
  );
};

/** Confirms the deletion. */
const ModalDelete = ({
  show,
  vectorstore,
  onOk,
  onCancel,
}: {
  show: boolean;
  vectorstore: Vectorstore | null;
  onOk: () => void;
  onCancel: () => void;
}) => (
  <Modal show={show} title="Delete Vectorstore" onOk={onOk} onCancel={onCancel}>
    <p>
      Are you sure you want to delete vectorstore <strong>{vectorstore?.name}</strong>?
    </p>
    <p>
      <em>
        Its database, its documents and its snapshots are destroyed, and cannot be recovered. A vectorstore with
        deletion protection cannot be deleted.
      </em>
    </p>
  </Modal>
);

/** Shows the error message. */
const ModalError = ({
  show,
  vectorstore,
  message,
  onClose,
}: {
  show: boolean;
  vectorstore: Vectorstore | null;
  message: string;
  onClose: () => void;
}) => (
  <Modal show={show} title="❌ Error" onClose={onClose}>
    <p>
      An error occurred while performing the operation on vectorstore <strong>{vectorstore?.name}</strong>.
    </p>
    <p>{message ? <span className="text-danger">{message}</span> : <em>An unknown error occurred.</em>}</p>
  </Modal>
);

/** Confirms that the operation succeeded. */
const ModalConfirmation = ({
  show,
  vectorstore,
  message,
  onClose,
}: {
  show: boolean;
  vectorstore: Vectorstore | null;
  message: string;
  onClose: () => void;
}) => (
  <Modal show={show} title="✅ Success" onClose={onClose}>
    <p>
      {message} <strong>{vectorstore?.name}</strong>.
    </p>
    <p>
      <em>Operation completed successfully.</em>
    </p>
  </Modal>
);

interface ToolbarProps {
  sessionContext: SessionContext;
  vectorstore: Vectorstore;
  onRequery: () => void;
}

export const Toolbar = ({ sessionContext, vectorstore, onRequery }: ToolbarProps) => {
  // this is a single way to control which and whether a modal is open.
  // it ensures that only one modal can be open at a time.
  const [modal, setModal] = useState<{ type: ModalType; vectorstore: Vectorstore | null }>({
    type: null,
    vectorstore: null,
  });
  const [errMessage, setErrMessage] = useState<string>("");
  const [successMessage, setSuccessMessage] = useState<string>("");

  const handleCloseModal = () => {
    setModal({ type: null, vectorstore: null });
  };
  const handleCloseModalWithRequery = () => {
    setModal({ type: null, vectorstore: null });
    onRequery();
  };

  /**
   * POST to one of the list API's actions, e.g. clone/12/new_name/, and show the result: the
   * confirmation modal on success, else the error modal with the server's error message.
   * See actionUrl() in @smarter/common for how the action's URL is built.
   */
  const runAction = (target: Vectorstore, path: string, verb: "clone" | "rename" | "delete") => {
    handleCloseModal();
    fetchDjangoUrl(sessionContext, actionUrl(sessionContext, path), JSON.stringify({}))
      .then(async (response) => {
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(`Failed to ${verb} vectorstore (${response.status}): ${data.error || response.statusText}`);
        }
        return data;
      })
      .then((data) => {
        console.debug(loggerPrefix, `Successfully ${verb}d vectorstore:`, data);
        setSuccessMessage(`Successfully ${verb}d vectorstore`);
        // clone and rename return the resulting vectorstore; delete returns a message.
        setModal({ type: "confirmation", vectorstore: data && data.id ? (data as Vectorstore) : target });
      })
      .catch((error) => {
        console.error(loggerPrefix, `Error trying to ${verb} vectorstore:`, error);
        setErrMessage(error.message);
        setModal({ type: "error", vectorstore: target });
      });
  };

  return (
    <>
      <div className="toolbar btn-group pe-2" role="group" aria-label="Actions">
        <a
          href={vectorstore.manifestUrl}
          className="btn btn-icon btn-sm border"
          title="Chat: Open the vectorstore workbench"
          tabIndex={0}
        >
          <i className="bi bi-chat-dots md-teal" />
        </a>
        <a
          href={vectorstore.manifestUrl}
          className="btn btn-icon btn-sm border"
          title="Edit: Open the YAML manifest that defines this vectorstore resource"
          tabIndex={0}
        >
          <i className="bi bi-pencil-square md-blue" />
        </a>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Clone: Clone this vectorstore resource to a new resource owned by you"
          onClick={() => setModal({ type: "clone", vectorstore })}
          tabIndex={0}
        >
          <i className="bi bi-files md-green" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Rename: Rename this vectorstore resource"
          onClick={() => setModal({ type: "rename", vectorstore })}
          tabIndex={0}
        >
          <i className="bi bi-pencil md-blue" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title={
            vectorstore.canDelete === false
              ? "Delete: You can't delete this vectorstore, because other resources depend on it, or you don't have permission to delete it"
              : "Delete: Delete this vectorstore resource"
          }
          onClick={() => setModal({ type: "delete", vectorstore })}
          disabled={vectorstore.canDelete === false}
          tabIndex={0}
        >
          <i className="bi bi-trash md-red" />
        </button>
      </div>

      <div>
        {modal.type === "clone" && (
          <ModalClone
            vectorstore={modal.vectorstore}
            onOk={(newName) => runAction(modal.vectorstore!, `clone/${modal.vectorstore!.id}/${newName}/`, "clone")}
            onCancel={handleCloseModal}
          />
        )}
        {modal.type === "rename" && (
          <ModalRename
            vectorstore={modal.vectorstore}
            onOk={(newName) => runAction(modal.vectorstore!, `rename/${modal.vectorstore!.id}/${newName}/`, "rename")}
            onCancel={handleCloseModal}
          />
        )}
        <ModalDelete
          show={modal.type === "delete"}
          vectorstore={modal.vectorstore}
          onOk={() => runAction(modal.vectorstore!, `delete/${modal.vectorstore!.id}/`, "delete")}
          onCancel={handleCloseModal}
        />
        <ModalError
          show={modal.type === "error"}
          vectorstore={modal.vectorstore}
          message={errMessage}
          onClose={handleCloseModal}
        />
        <ModalConfirmation
          show={modal.type === "confirmation"}
          vectorstore={modal.vectorstore}
          message={successMessage}
          onClose={handleCloseModalWithRequery}
        />
      </div>
    </>
  );
};

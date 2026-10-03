/**
 * Toolbar React Component
 *
 * This component provides a toolbar for managing vectorsearch resources, used in both ListView and CardView displays.
 * It offers actions for opening, editing, cloning, renaming, and deleting a vectorsearch, with modal dialogs for confirmation and error handling.
 *
 * Features:
 * - Action buttons for: Open (chat), Edit (YAML manifest), Clone, Rename, and Delete vectorsearch resources.
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
 * - vectorsearch (Vectorsearch): The vectorsearch resource to manage.
 *
 * Usage:
 * <Toolbar sessionContext={sessionContext} vectorsearch={vectorsearch} onRequery={onRequery} />
 *
 * This component is intended to be embedded in each vectorsearch row or card in ListView and CardView.
 */
import { useState } from "react";
import type { SessionContext } from "@smarter/common";
import { actionUrl, fetchDjangoUrl, Modal } from "@smarter/common";

import { loggerPrefix } from "@/lib/const";
import type { Vectorsearch } from "@/lib/Types";
import "./styles.css";

type ModalType = null | "clone" | "rename" | "delete" | "confirmation" | "error";

interface NameModalProps {
  vectorsearch: Vectorsearch | null;
  onOk: (newName: string) => void;
  onCancel: () => void;
}

/** Asks for the name of the clone. It is mounted only while open, so it starts empty. */
const ModalClone = ({ vectorsearch, onOk, onCancel }: NameModalProps) => {
  const [inputValue, setInputValue] = useState("");
  return (
    <Modal show title="Clone Vectorsearch" onOk={() => onOk(inputValue)} onCancel={onCancel}>
      <p>
        Clone vectorsearch <strong>{vectorsearch?.name}</strong> to a new resource owned by you.
      </p>
      <p>
        <em>Provide the new name for the cloned vectorsearch.</em>
      </p>
      <input value={inputValue} onChange={(e) => setInputValue(e.target.value)} placeholder="Enter new vectorsearch name" />
    </Modal>
  );
};

/** Asks for the new name. It is mounted only while open, so it starts with the current name. */
const ModalRename = ({ vectorsearch, onOk, onCancel }: NameModalProps) => {
  const [inputValue, setInputValue] = useState(vectorsearch?.name || "");
  return (
    <Modal show title="Rename Vectorsearch" onOk={() => onOk(inputValue)} onCancel={onCancel}>
      <p>
        Rename vectorsearch <strong>{vectorsearch?.name}</strong>.
      </p>
      <p>
        <em>Provide the new name for the vectorsearch.</em>
      </p>
      <input value={inputValue} onChange={(e) => setInputValue(e.target.value)} placeholder="Enter new vectorsearch name" />
    </Modal>
  );
};

/** Confirms the deletion. */
const ModalDelete = ({
  show,
  vectorsearch,
  onOk,
  onCancel,
}: {
  show: boolean;
  vectorsearch: Vectorsearch | null;
  onOk: () => void;
  onCancel: () => void;
}) => (
  <Modal show={show} title="Delete Vectorsearch" onOk={onOk} onCancel={onCancel}>
    <p>
      Are you sure you want to delete vectorsearch <strong>{vectorsearch?.name}</strong>?
    </p>
    <p>
      <em>Data is not recoverable.</em>
    </p>
  </Modal>
);

/** Shows the error message. */
const ModalError = ({
  show,
  vectorsearch,
  message,
  onClose,
}: {
  show: boolean;
  vectorsearch: Vectorsearch | null;
  message: string;
  onClose: () => void;
}) => (
  <Modal show={show} title="❌ Error" onClose={onClose}>
    <p>
      An error occurred while performing the operation on vectorsearch <strong>{vectorsearch?.name}</strong>.
    </p>
    <p>{message ? <span className="text-danger">{message}</span> : <em>An unknown error occurred.</em>}</p>
  </Modal>
);

/** Confirms that the operation succeeded. */
const ModalConfirmation = ({
  show,
  vectorsearch,
  message,
  onClose,
}: {
  show: boolean;
  vectorsearch: Vectorsearch | null;
  message: string;
  onClose: () => void;
}) => (
  <Modal show={show} title="✅ Success" onClose={onClose}>
    <p>
      {message} <strong>{vectorsearch?.name}</strong>.
    </p>
    <p>
      <em>Operation completed successfully.</em>
    </p>
  </Modal>
);

interface ToolbarProps {
  sessionContext: SessionContext;
  vectorsearch: Vectorsearch;
  onRequery: () => void;
}

export const Toolbar = ({ sessionContext, vectorsearch, onRequery }: ToolbarProps) => {
  // this is a single way to control which and whether a modal is open.
  // it ensures that only one modal can be open at a time.
  const [modal, setModal] = useState<{ type: ModalType; vectorsearch: Vectorsearch | null }>({ type: null, vectorsearch: null });
  const [errMessage, setErrMessage] = useState<string>("");
  const [successMessage, setSuccessMessage] = useState<string>("");

  const handleCloseModal = () => {
    setModal({ type: null, vectorsearch: null });
  };
  const handleCloseModalWithRequery = () => {
    setModal({ type: null, vectorsearch: null });
    onRequery();
  };

  /**
   * POST to one of the list API's actions, e.g. clone/12/new_name/, and show the result: the
   * confirmation modal on success, else the error modal with the server's error message.
   * See actionUrl() in @smarter/common for how the action's URL is built.
   */
  const runAction = (target: Vectorsearch, path: string, verb: "clone" | "rename" | "delete") => {
    handleCloseModal();
    fetchDjangoUrl(sessionContext, actionUrl(sessionContext, path), JSON.stringify({}))
      .then(async (response) => {
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(`Failed to ${verb} vectorsearch (${response.status}): ${data.error || response.statusText}`);
        }
        return data;
      })
      .then((data) => {
        console.debug(loggerPrefix, `Successfully ${verb}d vectorsearch:`, data);
        setSuccessMessage(`Successfully ${verb}d vectorsearch`);
        // clone and rename return the resulting vectorsearch; delete returns a message.
        setModal({ type: "confirmation", vectorsearch: data && data.id ? (data as Vectorsearch) : target });
      })
      .catch((error) => {
        console.error(loggerPrefix, `Error trying to ${verb} vectorsearch:`, error);
        setErrMessage(error.message);
        setModal({ type: "error", vectorsearch: target });
      });
  };

  return (
    <>
      <div className="toolbar btn-group pe-2" role="group" aria-label="Actions">
        <a
          href={vectorsearch.manifestUrl}
          className="btn btn-icon btn-sm border"
          title="Chat: Open the vectorsearch workbench"
          tabIndex={0}
        >
          <i className="bi bi-chat-dots md-teal" />
        </a>
        <a
          href={vectorsearch.manifestUrl}
          className="btn btn-icon btn-sm border"
          title="Edit: Open the YAML manifest that defines this vectorsearch resource"
          tabIndex={0}
        >
          <i className="bi bi-pencil-square md-blue" />
        </a>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Clone: Clone this vectorsearch resource to a new resource owned by you"
          onClick={() => setModal({ type: "clone", vectorsearch })}
          tabIndex={0}
        >
          <i className="bi bi-files md-green" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Rename: Rename this vectorsearch resource"
          onClick={() => setModal({ type: "rename", vectorsearch })}
          tabIndex={0}
        >
          <i className="bi bi-pencil md-blue" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title={
            vectorsearch.canDelete === false
              ? "Delete: You can't delete this vectorsearch, because other resources depend on it, or you don't have permission to delete it"
              : "Delete: Delete this vectorsearch resource"
          }
          onClick={() => setModal({ type: "delete", vectorsearch })}
          disabled={vectorsearch.canDelete === false}
          tabIndex={0}
        >
          <i className="bi bi-trash md-red" />
        </button>
      </div>

      <div>
        {modal.type === "clone" && (
          <ModalClone
            vectorsearch={modal.vectorsearch}
            onOk={(newName) => runAction(modal.vectorsearch!, `clone/${modal.vectorsearch!.id}/${newName}/`, "clone")}
            onCancel={handleCloseModal}
          />
        )}
        {modal.type === "rename" && (
          <ModalRename
            vectorsearch={modal.vectorsearch}
            onOk={(newName) => runAction(modal.vectorsearch!, `rename/${modal.vectorsearch!.id}/${newName}/`, "rename")}
            onCancel={handleCloseModal}
          />
        )}
        <ModalDelete
          show={modal.type === "delete"}
          vectorsearch={modal.vectorsearch}
          onOk={() => runAction(modal.vectorsearch!, `delete/${modal.vectorsearch!.id}/`, "delete")}
          onCancel={handleCloseModal}
        />
        <ModalError show={modal.type === "error"} vectorsearch={modal.vectorsearch} message={errMessage} onClose={handleCloseModal} />
        <ModalConfirmation
          show={modal.type === "confirmation"}
          vectorsearch={modal.vectorsearch}
          message={successMessage}
          onClose={handleCloseModalWithRequery}
        />
      </div>
    </>
  );
};

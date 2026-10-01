/**
 * Toolbar React Component
 *
 * This component provides a toolbar for managing mcpclient resources, used in both ListView and CardView displays.
 * It offers actions for opening, editing, cloning, renaming, and deleting a mcpclient, with modal dialogs for confirmation and error handling.
 *
 * Features:
 * - Action buttons for: Open (chat), Edit (YAML manifest), Clone, Rename, and Delete mcpclient resources.
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
 * - mcpclient (MCPClient): The mcpclient resource to manage.
 *
 * Usage:
 * <Toolbar sessionContext={sessionContext} mcpclient={mcpclient} onRequery={onRequery} />
 *
 * This component is intended to be embedded in each mcpclient row or card in ListView and CardView.
 */
import { useState } from "react";
import type { SessionContext } from "@smarter/common";
import { actionUrl, fetchDjangoUrl, Modal } from "@smarter/common";

import { loggerPrefix } from "@/lib/const";
import type { MCPClient } from "@/lib/Types";

type ModalType = null | "clone" | "rename" | "delete" | "confirmation" | "error";

interface NameModalProps {
  mcpclient: MCPClient | null;
  onOk: (newName: string) => void;
  onCancel: () => void;
}

/** Asks for the name of the clone. It is mounted only while open, so it starts empty. */
const ModalClone = ({ mcpclient, onOk, onCancel }: NameModalProps) => {
  const [inputValue, setInputValue] = useState("");
  return (
    <Modal show title="Clone MCPClient" onOk={() => onOk(inputValue)} onCancel={onCancel}>
      <p>
        Clone mcpclient <strong>{mcpclient?.name}</strong> to a new resource owned by you.
      </p>
      <p>
        <em>Provide the new name for the cloned mcpclient.</em>
      </p>
      <input value={inputValue} onChange={(e) => setInputValue(e.target.value)} placeholder="Enter new mcpclient name" />
    </Modal>
  );
};

/** Asks for the new name. It is mounted only while open, so it starts with the current name. */
const ModalRename = ({ mcpclient, onOk, onCancel }: NameModalProps) => {
  const [inputValue, setInputValue] = useState(mcpclient?.name || "");
  return (
    <Modal show title="Rename MCPClient" onOk={() => onOk(inputValue)} onCancel={onCancel}>
      <p>
        Rename mcpclient <strong>{mcpclient?.name}</strong>.
      </p>
      <p>
        <em>Provide the new name for the mcpclient.</em>
      </p>
      <input value={inputValue} onChange={(e) => setInputValue(e.target.value)} placeholder="Enter new mcpclient name" />
    </Modal>
  );
};

/** Confirms the deletion. */
const ModalDelete = ({
  show,
  mcpclient,
  onOk,
  onCancel,
}: {
  show: boolean;
  mcpclient: MCPClient | null;
  onOk: () => void;
  onCancel: () => void;
}) => (
  <Modal show={show} title="Delete MCPClient" onOk={onOk} onCancel={onCancel}>
    <p>
      Are you sure you want to delete mcpclient <strong>{mcpclient?.name}</strong>?
    </p>
    <p>
      <em>Data is not recoverable.</em>
    </p>
  </Modal>
);

/** Shows the error message. */
const ModalError = ({
  show,
  mcpclient,
  message,
  onClose,
}: {
  show: boolean;
  mcpclient: MCPClient | null;
  message: string;
  onClose: () => void;
}) => (
  <Modal show={show} title="❌ Error" onClose={onClose}>
    <p>
      An error occurred while performing the operation on mcpclient <strong>{mcpclient?.name}</strong>.
    </p>
    <p>{message ? <span className="text-danger">{message}</span> : <em>An unknown error occurred.</em>}</p>
  </Modal>
);

/** Confirms that the operation succeeded. */
const ModalConfirmation = ({
  show,
  mcpclient,
  message,
  onClose,
}: {
  show: boolean;
  mcpclient: MCPClient | null;
  message: string;
  onClose: () => void;
}) => (
  <Modal show={show} title="✅ Success" onClose={onClose}>
    <p>
      {message} <strong>{mcpclient?.name}</strong>.
    </p>
    <p>
      <em>Operation completed successfully.</em>
    </p>
  </Modal>
);

interface ToolbarProps {
  sessionContext: SessionContext;
  mcpclient: MCPClient;
  onRequery: () => void;
}

export const Toolbar = ({ sessionContext, mcpclient, onRequery }: ToolbarProps) => {
  // this is a single way to control which and whether a modal is open.
  // it ensures that only one modal can be open at a time.
  const [modal, setModal] = useState<{ type: ModalType; mcpclient: MCPClient | null }>({ type: null, mcpclient: null });
  const [errMessage, setErrMessage] = useState<string>("");
  const [successMessage, setSuccessMessage] = useState<string>("");

  const handleCloseModal = () => {
    setModal({ type: null, mcpclient: null });
  };
  const handleCloseModalWithRequery = () => {
    setModal({ type: null, mcpclient: null });
    onRequery();
  };

  /**
   * POST to one of the list API's actions, e.g. clone/12/new_name/, and show the result: the
   * confirmation modal on success, else the error modal with the server's error message.
   * See actionUrl() in @smarter/common for how the action's URL is built.
   */
  const runAction = (target: MCPClient, path: string, verb: "clone" | "rename" | "delete") => {
    handleCloseModal();
    fetchDjangoUrl(sessionContext, actionUrl(sessionContext, path), JSON.stringify({}))
      .then(async (response) => {
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(`Failed to ${verb} mcpclient (${response.status}): ${data.error || response.statusText}`);
        }
        return data;
      })
      .then((data) => {
        console.debug(loggerPrefix, `Successfully ${verb}d mcpclient:`, data);
        setSuccessMessage(`Successfully ${verb}d mcpclient`);
        // clone and rename return the resulting mcpclient; delete returns a message.
        setModal({ type: "confirmation", mcpclient: data && data.id ? (data as MCPClient) : target });
      })
      .catch((error) => {
        console.error(loggerPrefix, `Error trying to ${verb} mcpclient:`, error);
        setErrMessage(error.message);
        setModal({ type: "error", mcpclient: target });
      });
  };

  return (
    <>
      <div className="toolbar btn-group pe-2" role="group" aria-label="Actions">
        <a
          href={mcpclient.manifestUrl}
          className="btn btn-icon btn-sm border"
          title="Chat: Open the mcpclient workbench"
          tabIndex={0}
        >
          <i className="bi bi-chat-dots" />
        </a>
        <a
          href={mcpclient.manifestUrl}
          className="btn btn-icon btn-sm border"
          title="Edit: Open the YAML manifest that defines this mcpclient resource"
          tabIndex={0}
        >
          <i className="bi bi-pencil-square" />
        </a>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Clone: Clone this mcpclient resource to a new resource owned by you"
          onClick={() => setModal({ type: "clone", mcpclient })}
          tabIndex={0}
        >
          <i className="bi bi-files" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Rename: Rename this mcpclient resource"
          onClick={() => setModal({ type: "rename", mcpclient })}
          tabIndex={0}
        >
          <i className="bi bi-pencil" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Delete: Delete this mcpclient resource"
          onClick={() => setModal({ type: "delete", mcpclient })}
          tabIndex={0}
        >
          <i className="bi bi-trash" />
        </button>
      </div>

      <div>
        {modal.type === "clone" && (
          <ModalClone
            mcpclient={modal.mcpclient}
            onOk={(newName) => runAction(modal.mcpclient!, `clone/${modal.mcpclient!.id}/${newName}/`, "clone")}
            onCancel={handleCloseModal}
          />
        )}
        {modal.type === "rename" && (
          <ModalRename
            mcpclient={modal.mcpclient}
            onOk={(newName) => runAction(modal.mcpclient!, `rename/${modal.mcpclient!.id}/${newName}/`, "rename")}
            onCancel={handleCloseModal}
          />
        )}
        <ModalDelete
          show={modal.type === "delete"}
          mcpclient={modal.mcpclient}
          onOk={() => runAction(modal.mcpclient!, `delete/${modal.mcpclient!.id}/`, "delete")}
          onCancel={handleCloseModal}
        />
        <ModalError show={modal.type === "error"} mcpclient={modal.mcpclient} message={errMessage} onClose={handleCloseModal} />
        <ModalConfirmation
          show={modal.type === "confirmation"}
          mcpclient={modal.mcpclient}
          message={successMessage}
          onClose={handleCloseModalWithRequery}
        />
      </div>
    </>
  );
};

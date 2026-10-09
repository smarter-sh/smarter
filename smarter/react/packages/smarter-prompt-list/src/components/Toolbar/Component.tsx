/**
 * Toolbar React Component
 *
 * This component provides a toolbar for managing llmclient resources, used in both ListView and CardView displays.
 * It offers actions for opening, editing, cloning, renaming, and deleting a llmclient, with modal dialogs for confirmation and error handling.
 *
 * Features:
 * - Action buttons for: Open (chat), Edit (YAML manifest), Clone, Rename, and Delete llmclient resources.
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
 * - llmclient (LLMClient): The llmclient resource to manage.
 *
 * Usage:
 * <Toolbar sessionContext={sessionContext} llmclient={llmclient} onRequery={onRequery} />
 *
 * This component is intended to be embedded in each llmclient row or card in ListView and CardView.
 */
import { useState } from "react";
import type { SessionContext } from "@smarter/common";
import { fetchDjangoUrl, Modal } from "@smarter/common";

import { loggerPrefix } from "@/const";
import type { LLMClient } from "@/lib/Types";
import "./styles.css";

type ModalType = null | "clone" | "rename" | "delete" | "confirmation" | "error";

interface NameModalProps {
  llmclient: LLMClient | null;
  onOk: (newName: string) => void;
  onCancel: () => void;
}

/** Asks for the name of the clone. It is mounted only while open, so it starts empty. */
const ModalClone = ({ llmclient, onOk, onCancel }: NameModalProps) => {
  const [inputValue, setInputValue] = useState("");
  return (
    <Modal show title="Clone LLMClient" onOk={() => onOk(inputValue)} onCancel={onCancel}>
      <p>
        Clone llmclient <strong>{llmclient?.name}</strong> to a new resource owned by you.
      </p>
      <p>
        <em>Provide the new name for the cloned llmclient.</em>
      </p>
      <input
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        placeholder="Enter new llmclient name"
      />
    </Modal>
  );
};

/** Asks for the new name. It is mounted only while open, so it starts with the current name. */
const ModalRename = ({ llmclient, onOk, onCancel }: NameModalProps) => {
  const [inputValue, setInputValue] = useState(llmclient?.name || "");
  return (
    <Modal show title="Rename LLMClient" onOk={() => onOk(inputValue)} onCancel={onCancel}>
      <p>
        Rename llmclient <strong>{llmclient?.name}</strong>.
      </p>
      <p>
        <em>Provide the new name for the llmclient.</em>
      </p>
      <input
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        placeholder="Enter new llmclient name"
      />
    </Modal>
  );
};

/** Confirms the deletion. */
const ModalDelete = ({
  show,
  llmclient,
  onOk,
  onCancel,
}: {
  show: boolean;
  llmclient: LLMClient | null;
  onOk: () => void;
  onCancel: () => void;
}) => (
  <Modal show={show} title="Delete LLMClient" onOk={onOk} onCancel={onCancel}>
    <p>
      Are you sure you want to delete llmclient <strong>{llmclient?.name}</strong>?
    </p>
    <p>
      <em>Data is not recoverable.</em>
    </p>
  </Modal>
);

/** Shows the error message. */
const ModalError = ({
  show,
  llmclient,
  message,
  onClose,
}: {
  show: boolean;
  llmclient: LLMClient | null;
  message: string;
  onClose: () => void;
}) => (
  <Modal show={show} title="❌ Error" onClose={onClose}>
    <p>
      An error occurred while performing the operation on llmclient <strong>{llmclient?.name}</strong>.
    </p>
    <p>{message ? <span className="text-danger">{message}</span> : <em>An unknown error occurred.</em>}</p>
  </Modal>
);

/** Confirms that the operation succeeded. */
const ModalConfirmation = ({
  show,
  llmclient,
  message,
  onClose,
}: {
  show: boolean;
  llmclient: LLMClient | null;
  message: string;
  onClose: () => void;
}) => (
  <Modal show={show} title="✅ Success" onClose={onClose}>
    <p>
      {message} <strong>{llmclient?.name}</strong>.
    </p>
    <p>
      <em>Operation completed successfully.</em>
    </p>
  </Modal>
);

interface ToolbarProps {
  sessionContext: SessionContext;
  llmclient: LLMClient;
  onRequery: () => void;
}

export const Toolbar = ({ sessionContext, llmclient, onRequery }: ToolbarProps) => {
  // this is a single way to control which and whether a modal is open.
  // it ensures that only one modal can be open at a time.
  const [modal, setModal] = useState<{ type: ModalType; llmclient: LLMClient | null }>({ type: null, llmclient: null });
  const [errMessage, setErrMessage] = useState<string>("");
  const [successMessage, setSuccessMessage] = useState<string>("");

  const handleCloseModal = () => {
    setModal({ type: null, llmclient: null });
  };
  const handleCloseModalWithRequery = () => {
    setModal({ type: null, llmclient: null });
    onRequery();
  };

  /**
   * POST to one of the list API's actions, e.g. clone/12/new_name/, and show the result: the
   * confirmation modal on success, else the error modal with the server's error message.
   *
   * Unlike the other list apps, whose actions are siblings of the list endpoint (see actionUrl()
   * in @smarter/common), the prompt app's actions are nested under it:
   * /workbench/api/listview/clone/<id>/<new_name>/. See smarter.apps.prompt.urls.
   */
  const runAction = (target: LLMClient, path: string, verb: "clone" | "rename" | "delete") => {
    handleCloseModal();
    fetchDjangoUrl(sessionContext, sessionContext.ApiUrl + path, JSON.stringify({}))
      .then(async (response) => {
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(`Failed to ${verb} llmclient (${response.status}): ${data.error || response.statusText}`);
        }
        return data;
      })
      .then((data) => {
        console.debug(loggerPrefix, `Successfully ${verb}d llmclient:`, data);
        setSuccessMessage(`Successfully ${verb}d llmclient`);
        // clone and rename return the resulting llmclient; delete returns a message.
        setModal({ type: "confirmation", llmclient: data && data.id ? (data as LLMClient) : target });
      })
      .catch((error) => {
        console.error(loggerPrefix, `Error trying to ${verb} llmclient:`, error);
        setErrMessage(error.message);
        setModal({ type: "error", llmclient: target });
      });
  };

  return (
    <>
      <div className="toolbar btn-group pe-2" role="group" aria-label="Actions">
        <a
          href={llmclient.urlChatapp}
          className="btn btn-icon btn-sm border"
          title="Chat: Open the prompt workbench"
          tabIndex={0}
        >
          <i className="bi bi-chat-dots md-teal" />
        </a>
        <a
          href={llmclient.manifestUrl}
          className="btn btn-icon btn-sm border"
          title="Edit: Open the YAML manifest that defines this llmclient resource"
          tabIndex={0}
        >
          <i className="bi bi-pencil-square md-blue" />
        </a>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Clone: Clone this llmclient resource to a new resource owned by you"
          onClick={() => setModal({ type: "clone", llmclient })}
          tabIndex={0}
        >
          <i className="bi bi-files md-green" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Rename: Rename this llmclient resource"
          onClick={() => setModal({ type: "rename", llmclient })}
          tabIndex={0}
        >
          <i className="bi bi-pencil md-blue" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title={
            llmclient.canDelete === false
              ? "Delete: You can't delete this llmclient, because other resources depend on it, or you don't have permission to delete it"
              : "Delete: Delete this llmclient resource"
          }
          onClick={() => setModal({ type: "delete", llmclient })}
          disabled={llmclient.canDelete === false}
          tabIndex={0}
        >
          <i className="bi bi-trash md-red" />
        </button>
      </div>

      <div>
        {modal.type === "clone" && (
          <ModalClone
            llmclient={modal.llmclient}
            onOk={(newName) => runAction(modal.llmclient!, `clone/${modal.llmclient!.id}/${newName}/`, "clone")}
            onCancel={handleCloseModal}
          />
        )}
        {modal.type === "rename" && (
          <ModalRename
            llmclient={modal.llmclient}
            onOk={(newName) => runAction(modal.llmclient!, `rename/${modal.llmclient!.id}/${newName}/`, "rename")}
            onCancel={handleCloseModal}
          />
        )}
        <ModalDelete
          show={modal.type === "delete"}
          llmclient={modal.llmclient}
          onOk={() => runAction(modal.llmclient!, `delete/${modal.llmclient!.id}/`, "delete")}
          onCancel={handleCloseModal}
        />
        <ModalError
          show={modal.type === "error"}
          llmclient={modal.llmclient}
          message={errMessage}
          onClose={handleCloseModal}
        />
        <ModalConfirmation
          show={modal.type === "confirmation"}
          llmclient={modal.llmclient}
          message={successMessage}
          onClose={handleCloseModalWithRequery}
        />
      </div>
    </>
  );
};

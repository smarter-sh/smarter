/**
 * Toolbar React Component
 *
 * This component provides a toolbar for managing provider resources, used in both ListView and CardView displays.
 * It offers actions for opening, editing, cloning, renaming, and deleting a provider, with modal dialogs for confirmation and error handling.
 *
 * Features:
 * - Action buttons for: Open (chat), Edit (YAML manifest), Clone, Rename, and Delete provider resources.
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
 * - provider (Provider): The provider resource to manage.
 *
 * Usage:
 * <Toolbar sessionContext={sessionContext} provider={provider} onRequery={onRequery} />
 *
 * This component is intended to be embedded in each provider row or card in ListView and CardView.
 */
import { useState } from "react";
import type { SessionContext } from "@smarter/common";
import { actionUrl, fetchDjangoUrl, Modal } from "@smarter/common";

import { loggerPrefix } from "@/lib/const";
import type { Provider } from "@/lib/Types";

type ModalType = null | "clone" | "rename" | "delete" | "confirmation" | "error";

interface NameModalProps {
  provider: Provider | null;
  onOk: (newName: string) => void;
  onCancel: () => void;
}

/** Asks for the name of the clone. It is mounted only while open, so it starts empty. */
const ModalClone = ({ provider, onOk, onCancel }: NameModalProps) => {
  const [inputValue, setInputValue] = useState("");
  return (
    <Modal show title="Clone Provider" onOk={() => onOk(inputValue)} onCancel={onCancel}>
      <p>
        Clone provider <strong>{provider?.name}</strong> to a new resource owned by you.
      </p>
      <p>
        <em>Provide the new name for the cloned provider.</em>
      </p>
      <input value={inputValue} onChange={(e) => setInputValue(e.target.value)} placeholder="Enter new provider name" />
    </Modal>
  );
};

/** Asks for the new name. It is mounted only while open, so it starts with the current name. */
const ModalRename = ({ provider, onOk, onCancel }: NameModalProps) => {
  const [inputValue, setInputValue] = useState(provider?.name || "");
  return (
    <Modal show title="Rename Provider" onOk={() => onOk(inputValue)} onCancel={onCancel}>
      <p>
        Rename provider <strong>{provider?.name}</strong>.
      </p>
      <p>
        <em>Provide the new name for the provider.</em>
      </p>
      <input value={inputValue} onChange={(e) => setInputValue(e.target.value)} placeholder="Enter new provider name" />
    </Modal>
  );
};

/** Confirms the deletion. */
const ModalDelete = ({
  show,
  provider,
  onOk,
  onCancel,
}: {
  show: boolean;
  provider: Provider | null;
  onOk: () => void;
  onCancel: () => void;
}) => (
  <Modal show={show} title="Delete Provider" onOk={onOk} onCancel={onCancel}>
    <p>
      Are you sure you want to delete provider <strong>{provider?.name}</strong>?
    </p>
    <p>
      <em>Data is not recoverable.</em>
    </p>
  </Modal>
);

/** Shows the error message. */
const ModalError = ({
  show,
  provider,
  message,
  onClose,
}: {
  show: boolean;
  provider: Provider | null;
  message: string;
  onClose: () => void;
}) => (
  <Modal show={show} title="❌ Error" onClose={onClose}>
    <p>
      An error occurred while performing the operation on provider <strong>{provider?.name}</strong>.
    </p>
    <p>{message ? <span className="text-danger">{message}</span> : <em>An unknown error occurred.</em>}</p>
  </Modal>
);

/** Confirms that the operation succeeded. */
const ModalConfirmation = ({
  show,
  provider,
  message,
  onClose,
}: {
  show: boolean;
  provider: Provider | null;
  message: string;
  onClose: () => void;
}) => (
  <Modal show={show} title="✅ Success" onClose={onClose}>
    <p>
      {message} <strong>{provider?.name}</strong>.
    </p>
    <p>
      <em>Operation completed successfully.</em>
    </p>
  </Modal>
);

interface ToolbarProps {
  sessionContext: SessionContext;
  provider: Provider;
  onRequery: () => void;
}

export const Toolbar = ({ sessionContext, provider, onRequery }: ToolbarProps) => {
  // this is a single way to control which and whether a modal is open.
  // it ensures that only one modal can be open at a time.
  const [modal, setModal] = useState<{ type: ModalType; provider: Provider | null }>({ type: null, provider: null });
  const [errMessage, setErrMessage] = useState<string>("");
  const [successMessage, setSuccessMessage] = useState<string>("");

  const handleCloseModal = () => {
    setModal({ type: null, provider: null });
  };
  const handleCloseModalWithRequery = () => {
    setModal({ type: null, provider: null });
    onRequery();
  };

  /**
   * POST to one of the list API's actions, e.g. clone/12/new_name/, and show the result: the
   * confirmation modal on success, else the error modal with the server's error message.
   * See actionUrl() in @smarter/common for how the action's URL is built.
   */
  const runAction = (target: Provider, path: string, verb: "clone" | "rename" | "delete") => {
    handleCloseModal();
    fetchDjangoUrl(sessionContext, actionUrl(sessionContext, path), JSON.stringify({}))
      .then(async (response) => {
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(`Failed to ${verb} provider (${response.status}): ${data.error || response.statusText}`);
        }
        return data;
      })
      .then((data) => {
        console.debug(loggerPrefix, `Successfully ${verb}d provider:`, data);
        setSuccessMessage(`Successfully ${verb}d provider`);
        // clone and rename return the resulting provider; delete returns a message.
        setModal({ type: "confirmation", provider: data && data.id ? (data as Provider) : target });
      })
      .catch((error) => {
        console.error(loggerPrefix, `Error trying to ${verb} provider:`, error);
        setErrMessage(error.message);
        setModal({ type: "error", provider: target });
      });
  };

  return (
    <>
      <div className="toolbar btn-group pe-2" role="group" aria-label="Actions">
        <a
          href={provider.manifestUrl}
          className="btn btn-icon btn-sm border"
          title="Chat: Open the provider workbench"
          tabIndex={0}
        >
          <i className="bi bi-chat-dots" />
        </a>
        <a
          href={provider.manifestUrl}
          className="btn btn-icon btn-sm border"
          title="Edit: Open the YAML manifest that defines this provider resource"
          tabIndex={0}
        >
          <i className="bi bi-pencil-square" />
        </a>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Clone: Clone this provider resource to a new resource owned by you"
          onClick={() => setModal({ type: "clone", provider })}
          tabIndex={0}
        >
          <i className="bi bi-files" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Rename: Rename this provider resource"
          onClick={() => setModal({ type: "rename", provider })}
          tabIndex={0}
        >
          <i className="bi bi-pencil" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Delete: Delete this provider resource"
          onClick={() => setModal({ type: "delete", provider })}
          tabIndex={0}
        >
          <i className="bi bi-trash" />
        </button>
      </div>

      <div>
        {modal.type === "clone" && (
          <ModalClone
            provider={modal.provider}
            onOk={(newName) => runAction(modal.provider!, `clone/${modal.provider!.id}/${newName}/`, "clone")}
            onCancel={handleCloseModal}
          />
        )}
        {modal.type === "rename" && (
          <ModalRename
            provider={modal.provider}
            onOk={(newName) => runAction(modal.provider!, `rename/${modal.provider!.id}/${newName}/`, "rename")}
            onCancel={handleCloseModal}
          />
        )}
        <ModalDelete
          show={modal.type === "delete"}
          provider={modal.provider}
          onOk={() => runAction(modal.provider!, `delete/${modal.provider!.id}/`, "delete")}
          onCancel={handleCloseModal}
        />
        <ModalError show={modal.type === "error"} provider={modal.provider} message={errMessage} onClose={handleCloseModal} />
        <ModalConfirmation
          show={modal.type === "confirmation"}
          provider={modal.provider}
          message={successMessage}
          onClose={handleCloseModalWithRequery}
        />
      </div>
    </>
  );
};

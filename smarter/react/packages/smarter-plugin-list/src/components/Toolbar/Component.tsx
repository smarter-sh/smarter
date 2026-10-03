/**
 * Toolbar React Component
 *
 * This component provides a toolbar for managing plugin resources, used in both ListView and CardView displays.
 * It offers actions for opening, editing, cloning, renaming, and deleting a plugin, with modal dialogs for confirmation and error handling.
 *
 * Features:
 * - Action buttons for: Open (chat), Edit (YAML manifest), Clone, Rename, and Delete plugin resources.
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
 * - plugin (Plugin): The plugin resource to manage.
 *
 * Usage:
 * <Toolbar sessionContext={sessionContext} plugin={plugin} onRequery={onRequery} />
 *
 * This component is intended to be embedded in each plugin row or card in ListView and CardView.
 */
import { useState } from "react";
import type { SessionContext } from "@smarter/common";
import { actionUrl, fetchDjangoUrl, Modal } from "@smarter/common";

import { loggerPrefix } from "@/lib/const";
import type { Plugin } from "@/lib/Types";

type ModalType = null | "clone" | "rename" | "delete" | "confirmation" | "error";

interface NameModalProps {
  plugin: Plugin | null;
  onOk: (newName: string) => void;
  onCancel: () => void;
}

/** Asks for the name of the clone. It is mounted only while open, so it starts empty. */
const ModalClone = ({ plugin, onOk, onCancel }: NameModalProps) => {
  const [inputValue, setInputValue] = useState("");
  return (
    <Modal show title="Clone Plugin" onOk={() => onOk(inputValue)} onCancel={onCancel}>
      <p>
        Clone plugin <strong>{plugin?.name}</strong> to a new resource owned by you.
      </p>
      <p>
        <em>Provide the new name for the cloned plugin.</em>
      </p>
      <input value={inputValue} onChange={(e) => setInputValue(e.target.value)} placeholder="Enter new plugin name" />
    </Modal>
  );
};

/** Asks for the new name. It is mounted only while open, so it starts with the current name. */
const ModalRename = ({ plugin, onOk, onCancel }: NameModalProps) => {
  const [inputValue, setInputValue] = useState(plugin?.name || "");
  return (
    <Modal show title="Rename Plugin" onOk={() => onOk(inputValue)} onCancel={onCancel}>
      <p>
        Rename plugin <strong>{plugin?.name}</strong>.
      </p>
      <p>
        <em>Provide the new name for the plugin.</em>
      </p>
      <input value={inputValue} onChange={(e) => setInputValue(e.target.value)} placeholder="Enter new plugin name" />
    </Modal>
  );
};

/** Confirms the deletion. */
const ModalDelete = ({
  show,
  plugin,
  onOk,
  onCancel,
}: {
  show: boolean;
  plugin: Plugin | null;
  onOk: () => void;
  onCancel: () => void;
}) => (
  <Modal show={show} title="Delete Plugin" onOk={onOk} onCancel={onCancel}>
    <p>
      Are you sure you want to delete plugin <strong>{plugin?.name}</strong>?
    </p>
    <p>
      <em>Data is not recoverable.</em>
    </p>
  </Modal>
);

/** Shows the error message. */
const ModalError = ({
  show,
  plugin,
  message,
  onClose,
}: {
  show: boolean;
  plugin: Plugin | null;
  message: string;
  onClose: () => void;
}) => (
  <Modal show={show} title="❌ Error" onClose={onClose}>
    <p>
      An error occurred while performing the operation on plugin <strong>{plugin?.name}</strong>.
    </p>
    <p>{message ? <span className="text-danger">{message}</span> : <em>An unknown error occurred.</em>}</p>
  </Modal>
);

/** Confirms that the operation succeeded. */
const ModalConfirmation = ({
  show,
  plugin,
  message,
  onClose,
}: {
  show: boolean;
  plugin: Plugin | null;
  message: string;
  onClose: () => void;
}) => (
  <Modal show={show} title="✅ Success" onClose={onClose}>
    <p>
      {message} <strong>{plugin?.name}</strong>.
    </p>
    <p>
      <em>Operation completed successfully.</em>
    </p>
  </Modal>
);

interface ToolbarProps {
  sessionContext: SessionContext;
  plugin: Plugin;
  onRequery: () => void;
}

export const Toolbar = ({ sessionContext, plugin, onRequery }: ToolbarProps) => {
  // this is a single way to control which and whether a modal is open.
  // it ensures that only one modal can be open at a time.
  const [modal, setModal] = useState<{ type: ModalType; plugin: Plugin | null }>({ type: null, plugin: null });
  const [errMessage, setErrMessage] = useState<string>("");
  const [successMessage, setSuccessMessage] = useState<string>("");

  const handleCloseModal = () => {
    setModal({ type: null, plugin: null });
  };
  const handleCloseModalWithRequery = () => {
    setModal({ type: null, plugin: null });
    onRequery();
  };

  /**
   * POST to one of the list API's actions, e.g. clone/12/new_name/, and show the result: the
   * confirmation modal on success, else the error modal with the server's error message.
   * See actionUrl() in @smarter/common for how the action's URL is built.
   */
  const runAction = (target: Plugin, path: string, verb: "clone" | "rename" | "delete") => {
    handleCloseModal();
    fetchDjangoUrl(sessionContext, actionUrl(sessionContext, path), JSON.stringify({}))
      .then(async (response) => {
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(`Failed to ${verb} plugin (${response.status}): ${data.error || response.statusText}`);
        }
        return data;
      })
      .then((data) => {
        console.debug(loggerPrefix, `Successfully ${verb}d plugin:`, data);
        setSuccessMessage(`Successfully ${verb}d plugin`);
        // clone and rename return the resulting plugin; delete returns a message.
        setModal({ type: "confirmation", plugin: data && data.id ? (data as Plugin) : target });
      })
      .catch((error) => {
        console.error(loggerPrefix, `Error trying to ${verb} plugin:`, error);
        setErrMessage(error.message);
        setModal({ type: "error", plugin: target });
      });
  };

  return (
    <>
      <div className="toolbar btn-group pe-2" role="group" aria-label="Actions">
        <a
          href={plugin.manifestUrl}
          className="btn btn-icon btn-sm border"
          title="Chat: Open the plugin workbench"
          tabIndex={0}
        >
          <i className="bi bi-chat-dots" />
        </a>
        <a
          href={plugin.manifestUrl}
          className="btn btn-icon btn-sm border"
          title="Edit: Open the YAML manifest that defines this plugin resource"
          tabIndex={0}
        >
          <i className="bi bi-pencil-square" />
        </a>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Clone: Clone this plugin resource to a new resource owned by you"
          onClick={() => setModal({ type: "clone", plugin })}
          tabIndex={0}
        >
          <i className="bi bi-files" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Rename: Rename this plugin resource"
          onClick={() => setModal({ type: "rename", plugin })}
          tabIndex={0}
        >
          <i className="bi bi-pencil" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title={
            plugin.canDelete === false
              ? "Delete: You can't delete this plugin, because other resources depend on it, or you don't have permission to delete it"
              : "Delete: Delete this plugin resource"
          }
          onClick={() => setModal({ type: "delete", plugin })}
          disabled={plugin.canDelete === false}
          tabIndex={0}
        >
          <i className="bi bi-trash" />
        </button>
      </div>

      <div>
        {modal.type === "clone" && (
          <ModalClone
            plugin={modal.plugin}
            onOk={(newName) => runAction(modal.plugin!, `clone/${modal.plugin!.id}/${newName}/`, "clone")}
            onCancel={handleCloseModal}
          />
        )}
        {modal.type === "rename" && (
          <ModalRename
            plugin={modal.plugin}
            onOk={(newName) => runAction(modal.plugin!, `rename/${modal.plugin!.id}/${newName}/`, "rename")}
            onCancel={handleCloseModal}
          />
        )}
        <ModalDelete
          show={modal.type === "delete"}
          plugin={modal.plugin}
          onOk={() => runAction(modal.plugin!, `delete/${modal.plugin!.id}/`, "delete")}
          onCancel={handleCloseModal}
        />
        <ModalError show={modal.type === "error"} plugin={modal.plugin} message={errMessage} onClose={handleCloseModal} />
        <ModalConfirmation
          show={modal.type === "confirmation"}
          plugin={modal.plugin}
          message={successMessage}
          onClose={handleCloseModalWithRequery}
        />
      </div>
    </>
  );
};

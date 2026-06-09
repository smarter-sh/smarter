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
 * - Handles API calls for clone, rename, and delete operations, with feedback on success or failure.
 * - Accessible with ARIA labels and keyboard navigation.
 *
 * Props:
 * - sessionContext (SessionContext): Contains authentication and API information for backend operations.
 * - plugin (Plugin): The plugin resource to manage.
 *
 * Usage:
 * <Toolbar sessionContext={sessionContext} plugin={plugin} />
 *
 * This component is intended to be embedded in each plugin row or card in ListView and CardView.
 */
import { useState } from "react";
import { loggerPrefix } from "@/lib/const";
import type { SessionContext } from "@smarter/common";
import type { Plugin } from "@/lib/Types";
import { Modal } from "@smarter/common";
import { fetchDjangoUrl } from "@smarter/common";

interface ToolbarProps {
  sessionContext: SessionContext;
  plugin: Plugin;
  onRequery: () => void;
}

export const Toolbar = ({ sessionContext, plugin, onRequery }: ToolbarProps) => {
  // this is a single way to control which and whether a modal is open.
  // it ensures that only one modal can be open at a time, and simplifies
  // the logic for opening and closing any of the four modals.
  // url: string, csrfToken: string, djangoSessionCookieName: string, csrfCookieName: string, cookieDomain: string
  const [modal, setModal] = useState<{
    type: null | "clone" | "rename" | "delete" | "confirmation" | "error";
    plugin: Plugin | null;
  }>({ type: null, plugin: null });
  const [errMessage, setErrMessage] = useState<string>("");
  const [successMessage, setSuccessMessage] = useState<string>("");

  const handleCloseModal = () => {
    setModal({ type: null, plugin: null });
  };
  const handleCloseModalWithRequery = () => {
    setModal({ type: null, plugin: null });
    onRequery();
  };

  const handleCloneButtonClicked = (plugin: Plugin) => setModal({ type: "clone", plugin });
  const handleRenameButtonClicked = (plugin: Plugin) => setModal({ type: "rename", plugin });
  const handleDeleteButtonClicked = (plugin: Plugin) => setModal({ type: "delete", plugin });

  const handleError = (plugin: Plugin) => {
    handleCloseModal();
    setModal({ type: "error", plugin });
  };

  const ModalClone = () => {
    const [inputValue, setInputValue] = useState("");
    return (
      <>
        <Modal
          show={modal.type === "clone"}
          title="Clone Plugin"
          onOk={() => handleClonePlugin(modal.plugin!, inputValue)}
          onCancel={handleCloseModal}
        >
          <p>
            Clone plugin <strong>{modal.plugin?.name}</strong> to a new resource owned by you.
          </p>
          <p>
            <em>Provide the new name for the cloned plugin.</em>
          </p>
          <input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Enter new plugin name"
          />
        </Modal>
      </>
    );
  };

  const ModalRename = () => {
    const [inputValue, setInputValue] = useState(modal.plugin?.name || "");
    return (
      <>
        <Modal
          show={modal.type === "rename"}
          title="Rename Plugin"
          onOk={() => handleRenamePlugin(modal.plugin!, inputValue)}
          onCancel={handleCloseModal}
        >
          <p>
            Rename plugin <strong>{modal.plugin?.name}</strong>.
          </p>
          <p>
            <em>Provide the new name for the plugin.</em>
          </p>
          <input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Enter new plugin name"
          />
        </Modal>
      </>
    );
  };

  const ModalDelete = () => {
    return (
      <>
        <Modal
          show={modal.type === "delete"}
          title="Delete Plugin"
          onOk={() => handleDeletePlugin(modal.plugin!)}
          onCancel={handleCloseModal}
        >
          <p>
            Are you sure you want to delete plugin <strong>{modal.plugin?.name}</strong>?
          </p>
          <p>
            <em>Data is not recoverable.</em>
          </p>
        </Modal>
      </>
    );
  };

  const ModalError = () => {
    return (
      <>
        <Modal show={modal.type === "error"} title="❌ Error" onClose={handleCloseModal}>
          <p>
            An error occurred while performing the operation on plugin <strong>{modal.plugin?.name}</strong>.
          </p>
          <p>{errMessage ? <span className="text-danger">{errMessage}</span> : <em>An unknown error occurred.</em>}</p>
        </Modal>
      </>
    );
  };

  const ModalConfirmation = () => {
    return (
      <>
        <Modal show={modal.type === "confirmation"} title="✅ Success" onClose={handleCloseModalWithRequery}>
          <p>
            {successMessage} <strong>{modal.plugin?.name}</strong>.
          </p>
          <p>
            <em>Operation completed successfully.</em>
          </p>
        </Modal>
      </>
    );
  };

  const handleClonePlugin = async (plugin: Plugin, new_name: string) => {
    // see: smarter.apps.plugin.urls for API urls
    // path("api/clone/<int:plugin_id>/<str:new_name>/", PluginListApiCloneView.as_view(), name=PluginReverseNames.listview_api_clone),
    //
    // implement the clone logic here, e.g. call an API route to perform the clone operation.
    // return a success or failure result.

    const url = sessionContext.ApiUrl + "clone/" + plugin.id + "/" + new_name + "/";
    handleCloseModal();
    fetchDjangoUrl(
      JSON.stringify({}),
      url,
      sessionContext.djangoSessionCookieName,
      sessionContext.csrfCookieName,
      sessionContext.cookieDomain,
    )
      .then((response) => {
        if (!response.ok) {
          return response
            .json()
            .then((errorData) => {
              const errorMessage = errorData.error || response.statusText;
              setErrMessage(errorMessage);
              throw new Error(`Failed to clone plugin (${response.status}): ${errorMessage}`);
            })
            .catch(() => {
              throw new Error(`Failed to clone plugin (${response.status}): ${response.statusText}`);
            });
        }
        return response.json();
      })
      .then((data: Plugin) => {
        console.debug(loggerPrefix, "Successfully cloned plugin:", data);
        setModal({ type: "confirmation", plugin: data as Plugin });
        setSuccessMessage(`Successfully cloned plugin`);
      })
      .catch((error) => {
        console.error(loggerPrefix, "Error cloning plugin:", error);
        setErrMessage(error.message);
        handleError(plugin);
      });
    return true;
  };

  const handleRenamePlugin = async (plugin: Plugin, newName: string) => {
    // implement the rename logic here, e.g. call an API route to perform the rename operation.
    // return a success or failure result.
    handleCloseModal();
    const url = sessionContext.ApiUrl + "rename/" + plugin.id + "/" + newName + "/";

    fetchDjangoUrl(
      JSON.stringify({}),
      url,
      sessionContext.djangoSessionCookieName,
      sessionContext.csrfCookieName,
      sessionContext.cookieDomain,
    )
      .then((response) => {
        if (!response.ok) {
          return response
            .json()
            .then((errorData) => {
              const errorMessage = errorData.error || response.statusText;
              throw new Error(`Failed to rename plugin (${response.status}): ${errorMessage}`);
            })
            .catch(() => {
              throw new Error(`Failed to rename plugin (${response.status}): ${response.statusText}`);
            });
        }
        return response.json();
      })
      .then((data: Plugin) => {
        console.debug(loggerPrefix, "Successfully renamed plugin:", data);
        setModal({ type: "confirmation", plugin: data as Plugin });
        setSuccessMessage(`Successfully renamed plugin`);
      })
      .catch((error) => {
        console.error(loggerPrefix, "Error renaming plugin:", error);
        setErrMessage(error.message);
        handleError(plugin);
      });
    return true;
  };

  const handleDeletePlugin = async (plugin: Plugin) => {
    // implement the delete logic here, e.g. call an API route to perform the delete operation.
    // return a success or failure result.
    handleCloseModal();
    const url = sessionContext.ApiUrl + "delete/" + plugin.id + "/";
    fetchDjangoUrl(
      JSON.stringify({}),
      url,
      sessionContext.djangoSessionCookieName,
      sessionContext.csrfCookieName,
      sessionContext.cookieDomain,
    )
      .then((response) => {
        if (!response.ok) {
          return response
            .json()
            .then((errorData) => {
              const errorMessage = errorData.error || response.statusText;
              throw new Error(`Failed to delete plugin (${response.status}): ${errorMessage}`);
            })
            .catch(() => {
              throw new Error(`Failed to delete plugin (${response.status}): ${response.statusText}`);
            });
        }
        return response.json();
      })
      .then(() => {
        console.debug(loggerPrefix, "Successfully deleted plugin:", plugin);
        setModal({ type: "confirmation", plugin });
        setSuccessMessage(`Successfully deleted plugin`);
      })
      .catch((error) => {
        console.error(loggerPrefix, "Error deleting plugin:", error);
        setErrMessage(error.message);
        handleError(plugin);
      });
    return true;
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
          onClick={() => handleCloneButtonClicked(plugin)}
          tabIndex={0}
        >
          <i className="bi bi-files" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Rename: Rename this plugin resource"
          onClick={() => handleRenameButtonClicked(plugin)}
          tabIndex={0}
        >
          <i className="bi bi-pencil" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Delete: Delete this plugin resource"
          onClick={() => handleDeleteButtonClicked(plugin)}
          tabIndex={0}
        >
          <i className="bi bi-trash" />
        </button>
      </div>

      <div>
        <ModalClone />
        <ModalRename />
        <ModalDelete />
        <ModalError />
        <ModalConfirmation />
      </div>
    </>
  );
};

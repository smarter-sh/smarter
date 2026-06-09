/**
 * Toolbar React Component
 *
 * This component provides a toolbar for managing connection resources, used in both ListView and CardView displays.
 * It offers actions for opening, editing, cloning, renaming, and deleting a connection, with modal dialogs for confirmation and error handling.
 *
 * Features:
 * - Action buttons for: Open (chat), Edit (YAML manifest), Clone, Rename, and Delete connection resources.
 * - Modal dialogs for clone, rename, delete, error, and confirmation workflows.
 * - Ensures only one modal is open at a time for clear user interaction.
 * - Handles API calls for clone, rename, and delete operations, with feedback on success or failure.
 * - Accessible with ARIA labels and keyboard navigation.
 *
 * Props:
 * - sessionContext (SessionContext): Contains authentication and API information for backend operations.
 * - connection (Connection): The connection resource to manage.
 *
 * Usage:
 * <Toolbar sessionContext={sessionContext} connection={connection} />
 *
 * This component is intended to be embedded in each connection row or card in ListView and CardView.
 */
import { useState } from "react";
import { loggerPrefix } from "@/lib/const";
import type { SessionContext } from "@smarter/common";
import type { Connection } from "@/lib/Types";
import { Modal } from "@smarter/common";
import { fetchDjangoUrl } from "@smarter/common";

interface ToolbarProps {
  sessionContext: SessionContext;
  connection: Connection;
  onRequery: () => void;
}

export const Toolbar = ({ sessionContext, connection, onRequery }: ToolbarProps) => {
  // this is a single way to control which and whether a modal is open.
  // it ensures that only one modal can be open at a time, and simplifies
  // the logic for opening and closing any of the four modals.
  // url: string, csrfToken: string, djangoSessionCookieName: string, csrfCookieName: string, cookieDomain: string
  const [modal, setModal] = useState<{
    type: null | "clone" | "rename" | "delete" | "confirmation" | "error";
    connection: Connection | null;
  }>({ type: null, connection: null });
  const [errMessage, setErrMessage] = useState<string>("");
  const [successMessage, setSuccessMessage] = useState<string>("");

  const handleCloseModal = () => {
    setModal({ type: null, connection: null });
  };
  const handleCloseModalWithRequery = () => {
    setModal({ type: null, connection: null });
    onRequery();
  };

  const handleCloneButtonClicked = (connection: Connection) => setModal({ type: "clone", connection });
  const handleRenameButtonClicked = (connection: Connection) => setModal({ type: "rename", connection });
  const handleDeleteButtonClicked = (connection: Connection) => setModal({ type: "delete", connection });

  const handleError = (connection: Connection) => {
    handleCloseModal();
    setModal({ type: "error", connection });
  };

  const ModalClone = () => {
    const [inputValue, setInputValue] = useState("");
    return (
      <>
        <Modal
          show={modal.type === "clone"}
          title="Clone Connection"
          onOk={() => handleCloneConnection(modal.connection!, inputValue)}
          onCancel={handleCloseModal}
        >
          <p>
            Clone connection <strong>{modal.connection?.name}</strong> to a new resource owned by you.
          </p>
          <p>
            <em>Provide the new name for the cloned connection.</em>
          </p>
          <input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Enter new connection name"
          />
        </Modal>
      </>
    );
  };

  const ModalRename = () => {
    const [inputValue, setInputValue] = useState(modal.connection?.name || "");
    return (
      <>
        <Modal
          show={modal.type === "rename"}
          title="Rename Connection"
          onOk={() => handleRenameConnection(modal.connection!, inputValue)}
          onCancel={handleCloseModal}
        >
          <p>
            Rename connection <strong>{modal.connection?.name}</strong>.
          </p>
          <p>
            <em>Provide the new name for the connection.</em>
          </p>
          <input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Enter new connection name"
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
          title="Delete Connection"
          onOk={() => handleDeleteConnection(modal.connection!)}
          onCancel={handleCloseModal}
        >
          <p>
            Are you sure you want to delete connection <strong>{modal.connection?.name}</strong>?
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
            An error occurred while performing the operation on connection <strong>{modal.connection?.name}</strong>.
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
            {successMessage} <strong>{modal.connection?.name}</strong>.
          </p>
          <p>
            <em>Operation completed successfully.</em>
          </p>
        </Modal>
      </>
    );
  };

  const handleCloneConnection = async (connection: Connection, new_name: string) => {
    // see: smarter.apps.connection.urls for API urls
    // path("api/clone/<int:connection_id>/<str:new_name>/", ConnectionListApiCloneView.as_view(), name=ConnectionReverseNames.listview_api_clone),
    //
    // implement the clone logic here, e.g. call an API route to perform the clone operation.
    // return a success or failure result.

    const url = sessionContext.ApiUrl + "clone/" + connection.id + "/" + new_name + "/";
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
              throw new Error(`Failed to clone connection (${response.status}): ${errorMessage}`);
            })
            .catch(() => {
              throw new Error(`Failed to clone connection (${response.status}): ${response.statusText}`);
            });
        }
        return response.json();
      })
      .then((data: Connection) => {
        console.debug(loggerPrefix, "Successfully cloned connection:", data);
        setModal({ type: "confirmation", connection: data as Connection });
        setSuccessMessage(`Successfully cloned connection`);
      })
      .catch((error) => {
        console.error(loggerPrefix, "Error cloning connection:", error);
        setErrMessage(error.message);
        handleError(connection);
      });
    return true;
  };

  const handleRenameConnection = async (connection: Connection, newName: string) => {
    // implement the rename logic here, e.g. call an API route to perform the rename operation.
    // return a success or failure result.
    handleCloseModal();
    const url = sessionContext.ApiUrl + "rename/" + connection.id + "/" + newName + "/";

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
              throw new Error(`Failed to rename connection (${response.status}): ${errorMessage}`);
            })
            .catch(() => {
              throw new Error(`Failed to rename connection (${response.status}): ${response.statusText}`);
            });
        }
        return response.json();
      })
      .then((data: Connection) => {
        console.debug(loggerPrefix, "Successfully renamed connection:", data);
        setModal({ type: "confirmation", connection: data as Connection });
        setSuccessMessage(`Successfully renamed connection`);
      })
      .catch((error) => {
        console.error(loggerPrefix, "Error renaming connection:", error);
        setErrMessage(error.message);
        handleError(connection);
      });
    return true;
  };

  const handleDeleteConnection = async (connection: Connection) => {
    // implement the delete logic here, e.g. call an API route to perform the delete operation.
    // return a success or failure result.
    handleCloseModal();
    const url = sessionContext.ApiUrl + "delete/" + connection.id + "/";
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
              throw new Error(`Failed to delete connection (${response.status}): ${errorMessage}`);
            })
            .catch(() => {
              throw new Error(`Failed to delete connection (${response.status}): ${response.statusText}`);
            });
        }
        return response.json();
      })
      .then(() => {
        console.debug(loggerPrefix, "Successfully deleted connection:", connection);
        setModal({ type: "confirmation", connection });
        setSuccessMessage(`Successfully deleted connection`);
      })
      .catch((error) => {
        console.error(loggerPrefix, "Error deleting connection:", error);
        setErrMessage(error.message);
        handleError(connection);
      });
    return true;
  };

  return (
    <>
      <div className="toolbar btn-group pe-2" role="group" aria-label="Actions">
        <a
          href={connection.manifestUrl}
          className="btn btn-icon btn-sm border"
          title="Chat: Open the connection workbench"
          tabIndex={0}
        >
          <i className="bi bi-chat-dots" />
        </a>
        <a
          href={connection.manifestUrl}
          className="btn btn-icon btn-sm border"
          title="Edit: Open the YAML manifest that defines this connection resource"
          tabIndex={0}
        >
          <i className="bi bi-pencil-square" />
        </a>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Clone: Clone this connection resource to a new resource owned by you"
          onClick={() => handleCloneButtonClicked(connection)}
          tabIndex={0}
        >
          <i className="bi bi-files" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Rename: Rename this connection resource"
          onClick={() => handleRenameButtonClicked(connection)}
          tabIndex={0}
        >
          <i className="bi bi-pencil" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Delete: Delete this connection resource"
          onClick={() => handleDeleteButtonClicked(connection)}
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

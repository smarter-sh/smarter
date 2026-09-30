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
 * - Handles API calls for clone, rename, and delete operations, with feedback on success or failure.
 * - Accessible with ARIA labels and keyboard navigation.
 *
 * Props:
 * - sessionContext (SessionContext): Contains authentication and API information for backend operations.
 * - mcpclient (MCPClient): The mcpclient resource to manage.
 *
 * Usage:
 * <Toolbar sessionContext={sessionContext} mcpclient={mcpclient} />
 *
 * This component is intended to be embedded in each mcpclient row or card in ListView and CardView.
 */
import { useState } from "react";
import type { SessionContext } from "@smarter/common";
import { fetchDjangoUrl, Modal } from "@smarter/common";

import { loggerPrefix } from "@/lib/const";
import type { MCPClient } from "@/lib/Types";

interface ToolbarProps {
  sessionContext: SessionContext;
  mcpclient: MCPClient;
  onRequery: () => void;
}

export const Toolbar = ({ sessionContext, mcpclient, onRequery }: ToolbarProps) => {
  // this is a single way to control which and whether a modal is open.
  // it ensures that only one modal can be open at a time, and simplifies
  // the logic for opening and closing any of the four modals.
  // url: string, csrfToken: string, djangoSessionCookieName: string, csrfCookieName: string, cookieDomain: string
  const [modal, setModal] = useState<{
    type: null | "clone" | "rename" | "delete" | "confirmation" | "error";
    mcpclient: MCPClient | null;
  }>({ type: null, mcpclient: null });
  const [errMessage, setErrMessage] = useState<string>("");
  const [successMessage, setSuccessMessage] = useState<string>("");

  const handleCloseModal = () => {
    setModal({ type: null, mcpclient: null });
  };
  const handleCloseModalWithRequery = () => {
    setModal({ type: null, mcpclient: null });
    onRequery();
  };

  const handleCloneButtonClicked = (mcpclient: MCPClient) => setModal({ type: "clone", mcpclient });
  const handleRenameButtonClicked = (mcpclient: MCPClient) => setModal({ type: "rename", mcpclient });
  const handleDeleteButtonClicked = (mcpclient: MCPClient) => setModal({ type: "delete", mcpclient });

  const handleError = (mcpclient: MCPClient) => {
    handleCloseModal();
    setModal({ type: "error", mcpclient });
  };

  const ModalClone = () => {
    const [inputValue, setInputValue] = useState("");
    return (
      <>
        <Modal
          show={modal.type === "clone"}
          title="Clone MCPClient"
          onOk={() => handleCloneMCPClient(modal.mcpclient!, inputValue)}
          onCancel={handleCloseModal}
        >
          <p>
            Clone mcpclient <strong>{modal.mcpclient?.name}</strong> to a new resource owned by you.
          </p>
          <p>
            <em>Provide the new name for the cloned mcpclient.</em>
          </p>
          <input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Enter new mcpclient name"
          />
        </Modal>
      </>
    );
  };

  const ModalRename = () => {
    const [inputValue, setInputValue] = useState(modal.mcpclient?.name || "");
    return (
      <>
        <Modal
          show={modal.type === "rename"}
          title="Rename MCPClient"
          onOk={() => handleRenameMCPClient(modal.mcpclient!, inputValue)}
          onCancel={handleCloseModal}
        >
          <p>
            Rename mcpclient <strong>{modal.mcpclient?.name}</strong>.
          </p>
          <p>
            <em>Provide the new name for the mcpclient.</em>
          </p>
          <input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Enter new mcpclient name"
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
          title="Delete MCPClient"
          onOk={() => handleDeleteMCPClient(modal.mcpclient!)}
          onCancel={handleCloseModal}
        >
          <p>
            Are you sure you want to delete mcpclient <strong>{modal.mcpclient?.name}</strong>?
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
            An error occurred while performing the operation on mcpclient <strong>{modal.mcpclient?.name}</strong>.
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
            {successMessage} <strong>{modal.mcpclient?.name}</strong>.
          </p>
          <p>
            <em>Operation completed successfully.</em>
          </p>
        </Modal>
      </>
    );
  };

  const handleCloneMCPClient = async (mcpclient: MCPClient, new_name: string) => {
    // see: smarter.apps.mcpclient.urls for API urls
    // path("api/clone/<int:mcpclient_id>/<str:new_name>/", MCPClientListApiCloneView.as_view(), name=MCPClientReverseNames.listview_api_clone),
    //
    // implement the clone logic here, e.g. call an API route to perform the clone operation.
    // return a success or failure result.

    const url = sessionContext.ApiUrl + "clone/" + mcpclient.id + "/" + new_name + "/";
    handleCloseModal();
    fetchDjangoUrl(
      sessionContext,
      url,
      JSON.stringify({}),
    )
      .then((response) => {
        if (!response.ok) {
          return response
            .json()
            .then((errorData) => {
              const errorMessage = errorData.error || response.statusText;
              setErrMessage(errorMessage);
              throw new Error(`Failed to clone mcpclient (${response.status}): ${errorMessage}`);
            })
            .catch(() => {
              throw new Error(`Failed to clone mcpclient (${response.status}): ${response.statusText}`);
            });
        }
        return response.json();
      })
      .then((data: MCPClient) => {
        console.debug(loggerPrefix, "Successfully cloned mcpclient:", data);
        setModal({ type: "confirmation", mcpclient: data as MCPClient });
        setSuccessMessage(`Successfully cloned mcpclient`);
      })
      .catch((error) => {
        console.error(loggerPrefix, "Error cloning mcpclient:", error);
        setErrMessage(error.message);
        handleError(mcpclient);
      });
    return true;
  };

  const handleRenameMCPClient = async (mcpclient: MCPClient, newName: string) => {
    // implement the rename logic here, e.g. call an API route to perform the rename operation.
    // return a success or failure result.
    handleCloseModal();
    const url = sessionContext.ApiUrl + "rename/" + mcpclient.id + "/" + newName + "/";

    fetchDjangoUrl(
      sessionContext,
      url,
      JSON.stringify({}),
    )
      .then((response) => {
        if (!response.ok) {
          return response
            .json()
            .then((errorData) => {
              const errorMessage = errorData.error || response.statusText;
              throw new Error(`Failed to rename mcpclient (${response.status}): ${errorMessage}`);
            })
            .catch(() => {
              throw new Error(`Failed to rename mcpclient (${response.status}): ${response.statusText}`);
            });
        }
        return response.json();
      })
      .then((data: MCPClient) => {
        console.debug(loggerPrefix, "Successfully renamed mcpclient:", data);
        setModal({ type: "confirmation", mcpclient: data as MCPClient });
        setSuccessMessage(`Successfully renamed mcpclient`);
      })
      .catch((error) => {
        console.error(loggerPrefix, "Error renaming mcpclient:", error);
        setErrMessage(error.message);
        handleError(mcpclient);
      });
    return true;
  };

  const handleDeleteMCPClient = async (mcpclient: MCPClient) => {
    // implement the delete logic here, e.g. call an API route to perform the delete operation.
    // return a success or failure result.
    handleCloseModal();
    const url = sessionContext.ApiUrl + "delete/" + mcpclient.id + "/";
    fetchDjangoUrl(
      sessionContext,
      url,
      JSON.stringify({}),
    )
      .then((response) => {
        if (!response.ok) {
          return response
            .json()
            .then((errorData) => {
              const errorMessage = errorData.error || response.statusText;
              throw new Error(`Failed to delete mcpclient (${response.status}): ${errorMessage}`);
            })
            .catch(() => {
              throw new Error(`Failed to delete mcpclient (${response.status}): ${response.statusText}`);
            });
        }
        return response.json();
      })
      .then(() => {
        console.debug(loggerPrefix, "Successfully deleted mcpclient:", mcpclient);
        setModal({ type: "confirmation", mcpclient });
        setSuccessMessage(`Successfully deleted mcpclient`);
      })
      .catch((error) => {
        console.error(loggerPrefix, "Error deleting mcpclient:", error);
        setErrMessage(error.message);
        handleError(mcpclient);
      });
    return true;
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
          onClick={() => handleCloneButtonClicked(mcpclient)}
          tabIndex={0}
        >
          <i className="bi bi-files" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Rename: Rename this mcpclient resource"
          onClick={() => handleRenameButtonClicked(mcpclient)}
          tabIndex={0}
        >
          <i className="bi bi-pencil" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Delete: Delete this mcpclient resource"
          onClick={() => handleDeleteButtonClicked(mcpclient)}
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

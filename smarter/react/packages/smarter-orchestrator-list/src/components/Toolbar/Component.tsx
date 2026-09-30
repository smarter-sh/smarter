/**
 * Toolbar React Component
 *
 * This component provides a toolbar for managing orchestrator resources, used in both ListView and CardView displays.
 * It offers actions for opening, editing, cloning, renaming, and deleting a orchestrator, with modal dialogs for confirmation and error handling.
 *
 * Features:
 * - Action buttons for: Open (chat), Edit (YAML manifest), Clone, Rename, and Delete orchestrator resources.
 * - Modal dialogs for clone, rename, delete, error, and confirmation workflows.
 * - Ensures only one modal is open at a time for clear user interaction.
 * - Handles API calls for clone, rename, and delete operations, with feedback on success or failure.
 * - Accessible with ARIA labels and keyboard navigation.
 *
 * Props:
 * - sessionContext (SessionContext): Contains authentication and API information for backend operations.
 * - orchestrator (Orchestrator): The orchestrator resource to manage.
 *
 * Usage:
 * <Toolbar sessionContext={sessionContext} orchestrator={orchestrator} />
 *
 * This component is intended to be embedded in each orchestrator row or card in ListView and CardView.
 */
import { useState } from "react";
import type { SessionContext } from "@smarter/common";
import { fetchDjangoUrl, Modal } from "@smarter/common";

import { loggerPrefix } from "@/lib/const";
import type { Orchestrator } from "@/lib/Types";

interface ToolbarProps {
  sessionContext: SessionContext;
  orchestrator: Orchestrator;
  onRequery: () => void;
}

export const Toolbar = ({ sessionContext, orchestrator, onRequery }: ToolbarProps) => {
  // this is a single way to control which and whether a modal is open.
  // it ensures that only one modal can be open at a time, and simplifies
  // the logic for opening and closing any of the four modals.
  // url: string, csrfToken: string, djangoSessionCookieName: string, csrfCookieName: string, cookieDomain: string
  const [modal, setModal] = useState<{
    type: null | "clone" | "rename" | "delete" | "confirmation" | "error";
    orchestrator: Orchestrator | null;
  }>({ type: null, orchestrator: null });
  const [errMessage, setErrMessage] = useState<string>("");
  const [successMessage, setSuccessMessage] = useState<string>("");

  const handleCloseModal = () => {
    setModal({ type: null, orchestrator: null });
  };
  const handleCloseModalWithRequery = () => {
    setModal({ type: null, orchestrator: null });
    onRequery();
  };

  const handleCloneButtonClicked = (orchestrator: Orchestrator) => setModal({ type: "clone", orchestrator });
  const handleRenameButtonClicked = (orchestrator: Orchestrator) => setModal({ type: "rename", orchestrator });
  const handleDeleteButtonClicked = (orchestrator: Orchestrator) => setModal({ type: "delete", orchestrator });

  const handleError = (orchestrator: Orchestrator) => {
    handleCloseModal();
    setModal({ type: "error", orchestrator });
  };

  const ModalClone = () => {
    const [inputValue, setInputValue] = useState("");
    return (
      <>
        <Modal
          show={modal.type === "clone"}
          title="Clone Orchestrator"
          onOk={() => handleCloneOrchestrator(modal.orchestrator!, inputValue)}
          onCancel={handleCloseModal}
        >
          <p>
            Clone orchestrator <strong>{modal.orchestrator?.name}</strong> to a new resource owned by you.
          </p>
          <p>
            <em>Provide the new name for the cloned orchestrator.</em>
          </p>
          <input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Enter new orchestrator name"
          />
        </Modal>
      </>
    );
  };

  const ModalRename = () => {
    const [inputValue, setInputValue] = useState(modal.orchestrator?.name || "");
    return (
      <>
        <Modal
          show={modal.type === "rename"}
          title="Rename Orchestrator"
          onOk={() => handleRenameOrchestrator(modal.orchestrator!, inputValue)}
          onCancel={handleCloseModal}
        >
          <p>
            Rename orchestrator <strong>{modal.orchestrator?.name}</strong>.
          </p>
          <p>
            <em>Provide the new name for the orchestrator.</em>
          </p>
          <input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Enter new orchestrator name"
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
          title="Delete Orchestrator"
          onOk={() => handleDeleteOrchestrator(modal.orchestrator!)}
          onCancel={handleCloseModal}
        >
          <p>
            Are you sure you want to delete orchestrator <strong>{modal.orchestrator?.name}</strong>?
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
            An error occurred while performing the operation on orchestrator <strong>{modal.orchestrator?.name}</strong>.
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
            {successMessage} <strong>{modal.orchestrator?.name}</strong>.
          </p>
          <p>
            <em>Operation completed successfully.</em>
          </p>
        </Modal>
      </>
    );
  };

  const handleCloneOrchestrator = async (orchestrator: Orchestrator, new_name: string) => {
    // see: smarter.apps.orchestrator.urls for API urls
    // path("api/clone/<int:orchestrator_id>/<str:new_name>/", OrchestratorListApiCloneView.as_view(), name=OrchestratorReverseNames.listview_api_clone),
    //
    // implement the clone logic here, e.g. call an API route to perform the clone operation.
    // return a success or failure result.

    const url = sessionContext.ApiUrl + "clone/" + orchestrator.id + "/" + new_name + "/";
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
              throw new Error(`Failed to clone orchestrator (${response.status}): ${errorMessage}`);
            })
            .catch(() => {
              throw new Error(`Failed to clone orchestrator (${response.status}): ${response.statusText}`);
            });
        }
        return response.json();
      })
      .then((data: Orchestrator) => {
        console.debug(loggerPrefix, "Successfully cloned orchestrator:", data);
        setModal({ type: "confirmation", orchestrator: data as Orchestrator });
        setSuccessMessage(`Successfully cloned orchestrator`);
      })
      .catch((error) => {
        console.error(loggerPrefix, "Error cloning orchestrator:", error);
        setErrMessage(error.message);
        handleError(orchestrator);
      });
    return true;
  };

  const handleRenameOrchestrator = async (orchestrator: Orchestrator, newName: string) => {
    // implement the rename logic here, e.g. call an API route to perform the rename operation.
    // return a success or failure result.
    handleCloseModal();
    const url = sessionContext.ApiUrl + "rename/" + orchestrator.id + "/" + newName + "/";

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
              throw new Error(`Failed to rename orchestrator (${response.status}): ${errorMessage}`);
            })
            .catch(() => {
              throw new Error(`Failed to rename orchestrator (${response.status}): ${response.statusText}`);
            });
        }
        return response.json();
      })
      .then((data: Orchestrator) => {
        console.debug(loggerPrefix, "Successfully renamed orchestrator:", data);
        setModal({ type: "confirmation", orchestrator: data as Orchestrator });
        setSuccessMessage(`Successfully renamed orchestrator`);
      })
      .catch((error) => {
        console.error(loggerPrefix, "Error renaming orchestrator:", error);
        setErrMessage(error.message);
        handleError(orchestrator);
      });
    return true;
  };

  const handleDeleteOrchestrator = async (orchestrator: Orchestrator) => {
    // implement the delete logic here, e.g. call an API route to perform the delete operation.
    // return a success or failure result.
    handleCloseModal();
    const url = sessionContext.ApiUrl + "delete/" + orchestrator.id + "/";
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
              throw new Error(`Failed to delete orchestrator (${response.status}): ${errorMessage}`);
            })
            .catch(() => {
              throw new Error(`Failed to delete orchestrator (${response.status}): ${response.statusText}`);
            });
        }
        return response.json();
      })
      .then(() => {
        console.debug(loggerPrefix, "Successfully deleted orchestrator:", orchestrator);
        setModal({ type: "confirmation", orchestrator });
        setSuccessMessage(`Successfully deleted orchestrator`);
      })
      .catch((error) => {
        console.error(loggerPrefix, "Error deleting orchestrator:", error);
        setErrMessage(error.message);
        handleError(orchestrator);
      });
    return true;
  };

  return (
    <>
      <div className="toolbar btn-group pe-2" role="group" aria-label="Actions">
        <a
          href={orchestrator.manifestUrl}
          className="btn btn-icon btn-sm border"
          title="Chat: Open the orchestrator workbench"
          tabIndex={0}
        >
          <i className="bi bi-chat-dots" />
        </a>
        <a
          href={orchestrator.manifestUrl}
          className="btn btn-icon btn-sm border"
          title="Edit: Open the YAML manifest that defines this orchestrator resource"
          tabIndex={0}
        >
          <i className="bi bi-pencil-square" />
        </a>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Clone: Clone this orchestrator resource to a new resource owned by you"
          onClick={() => handleCloneButtonClicked(orchestrator)}
          tabIndex={0}
        >
          <i className="bi bi-files" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Rename: Rename this orchestrator resource"
          onClick={() => handleRenameButtonClicked(orchestrator)}
          tabIndex={0}
        >
          <i className="bi bi-pencil" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Delete: Delete this orchestrator resource"
          onClick={() => handleDeleteButtonClicked(orchestrator)}
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

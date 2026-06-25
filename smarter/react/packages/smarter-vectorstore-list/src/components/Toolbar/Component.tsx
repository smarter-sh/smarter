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
 * - Handles API calls for clone, rename, and delete operations, with feedback on success or failure.
 * - Accessible with ARIA labels and keyboard navigation.
 *
 * Props:
 * - sessionContext (SessionContext): Contains authentication and API information for backend operations.
 * - vectorstore (Vectorestore): The vectorstore resource to manage.
 *
 * Usage:
 * <Toolbar sessionContext={sessionContext} vectorstore={vectorstore} />
 *
 * This component is intended to be embedded in each vectorstore row or card in ListView and CardView.
 */
import { useState } from "react";
import type { SessionContext } from "@smarter/common";
import { fetchDjangoUrl, Modal } from "@smarter/common";

import { loggerPrefix } from "@/lib/const";
import type { Vectorestore } from "@/lib/Types";

interface ToolbarProps {
  sessionContext: SessionContext;
  vectorstore: Vectorestore;
  onRequery: () => void;
}

export const Toolbar = ({ sessionContext, vectorstore, onRequery }: ToolbarProps) => {
  // this is a single way to control which and whether a modal is open.
  // it ensures that only one modal can be open at a time, and simplifies
  // the logic for opening and closing any of the four modals.
  // url: string, csrfToken: string, djangoSessionCookieName: string, csrfCookieName: string, cookieDomain: string
  const [modal, setModal] = useState<{
    type: null | "clone" | "rename" | "delete" | "confirmation" | "error";
    vectorstore: Vectorestore | null;
  }>({ type: null, vectorstore: null });
  const [errMessage, setErrMessage] = useState<string>("");
  const [successMessage, setSuccessMessage] = useState<string>("");

  const handleCloseModal = () => {
    setModal({ type: null, vectorstore: null });
  };
  const handleCloseModalWithRequery = () => {
    setModal({ type: null, vectorstore: null });
    onRequery();
  };

  const handleCloneButtonClicked = (vectorstore: Vectorestore) => setModal({ type: "clone", vectorstore });
  const handleRenameButtonClicked = (vectorstore: Vectorestore) => setModal({ type: "rename", vectorstore });
  const handleDeleteButtonClicked = (vectorstore: Vectorestore) => setModal({ type: "delete", vectorstore });

  const handleError = (vectorstore: Vectorestore) => {
    handleCloseModal();
    setModal({ type: "error", vectorstore });
  };

  const ModalClone = () => {
    const [inputValue, setInputValue] = useState("");
    return (
      <>
        <Modal
          show={modal.type === "clone"}
          title="Clone Vectorestore"
          onOk={() => handleCloneVectorestore(modal.vectorstore!, inputValue)}
          onCancel={handleCloseModal}
        >
          <p>
            Clone vectorstore <strong>{modal.vectorstore?.name}</strong> to a new resource owned by you.
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
      </>
    );
  };

  const ModalRename = () => {
    const [inputValue, setInputValue] = useState(modal.vectorstore?.name || "");
    return (
      <>
        <Modal
          show={modal.type === "rename"}
          title="Rename Vectorestore"
          onOk={() => handleRenameVectorestore(modal.vectorstore!, inputValue)}
          onCancel={handleCloseModal}
        >
          <p>
            Rename vectorstore <strong>{modal.vectorstore?.name}</strong>.
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
      </>
    );
  };

  const ModalDelete = () => {
    return (
      <>
        <Modal
          show={modal.type === "delete"}
          title="Delete Vectorestore"
          onOk={() => handleDeleteVectorestore(modal.vectorstore!)}
          onCancel={handleCloseModal}
        >
          <p>
            Are you sure you want to delete vectorstore <strong>{modal.vectorstore?.name}</strong>?
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
            An error occurred while performing the operation on vectorstore <strong>{modal.vectorstore?.name}</strong>.
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
            {successMessage} <strong>{modal.vectorstore?.name}</strong>.
          </p>
          <p>
            <em>Operation completed successfully.</em>
          </p>
        </Modal>
      </>
    );
  };

  const handleCloneVectorestore = async (vectorstore: Vectorestore, new_name: string) => {
    // see: smarter.apps.vectorstore.urls for API urls
    // path("api/clone/<int:vectorstore_id>/<str:new_name>/", VectorestoreListApiCloneView.as_view(), name=VectorestoreReverseNames.listview_api_clone),
    //
    // implement the clone logic here, e.g. call an API route to perform the clone operation.
    // return a success or failure result.

    const url = sessionContext.ApiUrl + "clone/" + vectorstore.id + "/" + new_name + "/";
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
              throw new Error(`Failed to clone vectorstore (${response.status}): ${errorMessage}`);
            })
            .catch(() => {
              throw new Error(`Failed to clone vectorstore (${response.status}): ${response.statusText}`);
            });
        }
        return response.json();
      })
      .then((data: Vectorestore) => {
        console.debug(loggerPrefix, "Successfully cloned vectorstore:", data);
        setModal({ type: "confirmation", vectorstore: data as Vectorestore });
        setSuccessMessage(`Successfully cloned vectorstore`);
      })
      .catch((error) => {
        console.error(loggerPrefix, "Error cloning vectorstore:", error);
        setErrMessage(error.message);
        handleError(vectorstore);
      });
    return true;
  };

  const handleRenameVectorestore = async (vectorstore: Vectorestore, newName: string) => {
    // implement the rename logic here, e.g. call an API route to perform the rename operation.
    // return a success or failure result.
    handleCloseModal();
    const url = sessionContext.ApiUrl + "rename/" + vectorstore.id + "/" + newName + "/";

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
              throw new Error(`Failed to rename vectorstore (${response.status}): ${errorMessage}`);
            })
            .catch(() => {
              throw new Error(`Failed to rename vectorstore (${response.status}): ${response.statusText}`);
            });
        }
        return response.json();
      })
      .then((data: Vectorestore) => {
        console.debug(loggerPrefix, "Successfully renamed vectorstore:", data);
        setModal({ type: "confirmation", vectorstore: data as Vectorestore });
        setSuccessMessage(`Successfully renamed vectorstore`);
      })
      .catch((error) => {
        console.error(loggerPrefix, "Error renaming vectorstore:", error);
        setErrMessage(error.message);
        handleError(vectorstore);
      });
    return true;
  };

  const handleDeleteVectorestore = async (vectorstore: Vectorestore) => {
    // implement the delete logic here, e.g. call an API route to perform the delete operation.
    // return a success or failure result.
    handleCloseModal();
    const url = sessionContext.ApiUrl + "delete/" + vectorstore.id + "/";
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
              throw new Error(`Failed to delete vectorstore (${response.status}): ${errorMessage}`);
            })
            .catch(() => {
              throw new Error(`Failed to delete vectorstore (${response.status}): ${response.statusText}`);
            });
        }
        return response.json();
      })
      .then(() => {
        console.debug(loggerPrefix, "Successfully deleted vectorstore:", vectorstore);
        setModal({ type: "confirmation", vectorstore });
        setSuccessMessage(`Successfully deleted vectorstore`);
      })
      .catch((error) => {
        console.error(loggerPrefix, "Error deleting vectorstore:", error);
        setErrMessage(error.message);
        handleError(vectorstore);
      });
    return true;
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
          <i className="bi bi-chat-dots" />
        </a>
        <a
          href={vectorstore.manifestUrl}
          className="btn btn-icon btn-sm border"
          title="Edit: Open the YAML manifest that defines this vectorstore resource"
          tabIndex={0}
        >
          <i className="bi bi-pencil-square" />
        </a>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Clone: Clone this vectorstore resource to a new resource owned by you"
          onClick={() => handleCloneButtonClicked(vectorstore)}
          tabIndex={0}
        >
          <i className="bi bi-files" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Rename: Rename this vectorstore resource"
          onClick={() => handleRenameButtonClicked(vectorstore)}
          tabIndex={0}
        >
          <i className="bi bi-pencil" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Delete: Delete this vectorstore resource"
          onClick={() => handleDeleteButtonClicked(vectorstore)}
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

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
 * - Handles API calls for clone, rename, and delete operations, with feedback on success or failure.
 * - Accessible with ARIA labels and keyboard navigation.
 *
 * Props:
 * - sessionContext (SessionContext): Contains authentication and API information for backend operations.
 * - vectorsearch (Vectorsearch): The vectorsearch resource to manage.
 *
 * Usage:
 * <Toolbar sessionContext={sessionContext} vectorsearch={vectorsearch} />
 *
 * This component is intended to be embedded in each vectorsearch row or card in ListView and CardView.
 */
import { useState } from "react";
import type { SessionContext } from "@smarter/common";
import { fetchDjangoUrl, Modal } from "@smarter/common";

import { loggerPrefix } from "@/lib/const";
import type { Vectorsearch } from "@/lib/Types";

interface ToolbarProps {
  sessionContext: SessionContext;
  vectorsearch: Vectorsearch;
  onRequery: () => void;
}

export const Toolbar = ({ sessionContext, vectorsearch, onRequery }: ToolbarProps) => {
  // this is a single way to control which and whether a modal is open.
  // it ensures that only one modal can be open at a time, and simplifies
  // the logic for opening and closing any of the four modals.
  // url: string, csrfToken: string, djangoSessionCookieName: string, csrfCookieName: string, cookieDomain: string
  const [modal, setModal] = useState<{
    type: null | "clone" | "rename" | "delete" | "confirmation" | "error";
    vectorsearch: Vectorsearch | null;
  }>({ type: null, vectorsearch: null });
  const [errMessage, setErrMessage] = useState<string>("");
  const [successMessage, setSuccessMessage] = useState<string>("");

  const handleCloseModal = () => {
    setModal({ type: null, vectorsearch: null });
  };
  const handleCloseModalWithRequery = () => {
    setModal({ type: null, vectorsearch: null });
    onRequery();
  };

  const handleCloneButtonClicked = (vectorsearch: Vectorsearch) => setModal({ type: "clone", vectorsearch });
  const handleRenameButtonClicked = (vectorsearch: Vectorsearch) => setModal({ type: "rename", vectorsearch });
  const handleDeleteButtonClicked = (vectorsearch: Vectorsearch) => setModal({ type: "delete", vectorsearch });

  const handleError = (vectorsearch: Vectorsearch) => {
    handleCloseModal();
    setModal({ type: "error", vectorsearch });
  };

  const ModalClone = () => {
    const [inputValue, setInputValue] = useState("");
    return (
      <>
        <Modal
          show={modal.type === "clone"}
          title="Clone Vectorsearch"
          onOk={() => handleCloneVectorsearch(modal.vectorsearch!, inputValue)}
          onCancel={handleCloseModal}
        >
          <p>
            Clone vectorsearch <strong>{modal.vectorsearch?.name}</strong> to a new resource owned by you.
          </p>
          <p>
            <em>Provide the new name for the cloned vectorsearch.</em>
          </p>
          <input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Enter new vectorsearch name"
          />
        </Modal>
      </>
    );
  };

  const ModalRename = () => {
    const [inputValue, setInputValue] = useState(modal.vectorsearch?.name || "");
    return (
      <>
        <Modal
          show={modal.type === "rename"}
          title="Rename Vectorsearch"
          onOk={() => handleRenameVectorsearch(modal.vectorsearch!, inputValue)}
          onCancel={handleCloseModal}
        >
          <p>
            Rename vectorsearch <strong>{modal.vectorsearch?.name}</strong>.
          </p>
          <p>
            <em>Provide the new name for the vectorsearch.</em>
          </p>
          <input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Enter new vectorsearch name"
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
          title="Delete Vectorsearch"
          onOk={() => handleDeleteVectorsearch(modal.vectorsearch!)}
          onCancel={handleCloseModal}
        >
          <p>
            Are you sure you want to delete vectorsearch <strong>{modal.vectorsearch?.name}</strong>?
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
            An error occurred while performing the operation on vectorsearch <strong>{modal.vectorsearch?.name}</strong>.
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
            {successMessage} <strong>{modal.vectorsearch?.name}</strong>.
          </p>
          <p>
            <em>Operation completed successfully.</em>
          </p>
        </Modal>
      </>
    );
  };

  const handleCloneVectorsearch = async (vectorsearch: Vectorsearch, new_name: string) => {
    // see: smarter.apps.vectorsearch.urls for API urls
    // path("api/clone/<int:vectorsearch_id>/<str:new_name>/", VectorsearchListApiCloneView.as_view(), name=VectorsearchReverseNames.listview_api_clone),
    //
    // implement the clone logic here, e.g. call an API route to perform the clone operation.
    // return a success or failure result.

    const url = sessionContext.ApiUrl + "clone/" + vectorsearch.id + "/" + new_name + "/";
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
              throw new Error(`Failed to clone vectorsearch (${response.status}): ${errorMessage}`);
            })
            .catch(() => {
              throw new Error(`Failed to clone vectorsearch (${response.status}): ${response.statusText}`);
            });
        }
        return response.json();
      })
      .then((data: Vectorsearch) => {
        console.debug(loggerPrefix, "Successfully cloned vectorsearch:", data);
        setModal({ type: "confirmation", vectorsearch: data as Vectorsearch });
        setSuccessMessage(`Successfully cloned vectorsearch`);
      })
      .catch((error) => {
        console.error(loggerPrefix, "Error cloning vectorsearch:", error);
        setErrMessage(error.message);
        handleError(vectorsearch);
      });
    return true;
  };

  const handleRenameVectorsearch = async (vectorsearch: Vectorsearch, newName: string) => {
    // implement the rename logic here, e.g. call an API route to perform the rename operation.
    // return a success or failure result.
    handleCloseModal();
    const url = sessionContext.ApiUrl + "rename/" + vectorsearch.id + "/" + newName + "/";

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
              throw new Error(`Failed to rename vectorsearch (${response.status}): ${errorMessage}`);
            })
            .catch(() => {
              throw new Error(`Failed to rename vectorsearch (${response.status}): ${response.statusText}`);
            });
        }
        return response.json();
      })
      .then((data: Vectorsearch) => {
        console.debug(loggerPrefix, "Successfully renamed vectorsearch:", data);
        setModal({ type: "confirmation", vectorsearch: data as Vectorsearch });
        setSuccessMessage(`Successfully renamed vectorsearch`);
      })
      .catch((error) => {
        console.error(loggerPrefix, "Error renaming vectorsearch:", error);
        setErrMessage(error.message);
        handleError(vectorsearch);
      });
    return true;
  };

  const handleDeleteVectorsearch = async (vectorsearch: Vectorsearch) => {
    // implement the delete logic here, e.g. call an API route to perform the delete operation.
    // return a success or failure result.
    handleCloseModal();
    const url = sessionContext.ApiUrl + "delete/" + vectorsearch.id + "/";
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
              throw new Error(`Failed to delete vectorsearch (${response.status}): ${errorMessage}`);
            })
            .catch(() => {
              throw new Error(`Failed to delete vectorsearch (${response.status}): ${response.statusText}`);
            });
        }
        return response.json();
      })
      .then(() => {
        console.debug(loggerPrefix, "Successfully deleted vectorsearch:", vectorsearch);
        setModal({ type: "confirmation", vectorsearch });
        setSuccessMessage(`Successfully deleted vectorsearch`);
      })
      .catch((error) => {
        console.error(loggerPrefix, "Error deleting vectorsearch:", error);
        setErrMessage(error.message);
        handleError(vectorsearch);
      });
    return true;
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
          <i className="bi bi-chat-dots" />
        </a>
        <a
          href={vectorsearch.manifestUrl}
          className="btn btn-icon btn-sm border"
          title="Edit: Open the YAML manifest that defines this vectorsearch resource"
          tabIndex={0}
        >
          <i className="bi bi-pencil-square" />
        </a>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Clone: Clone this vectorsearch resource to a new resource owned by you"
          onClick={() => handleCloneButtonClicked(vectorsearch)}
          tabIndex={0}
        >
          <i className="bi bi-files" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Rename: Rename this vectorsearch resource"
          onClick={() => handleRenameButtonClicked(vectorsearch)}
          tabIndex={0}
        >
          <i className="bi bi-pencil" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Delete: Delete this vectorsearch resource"
          onClick={() => handleDeleteButtonClicked(vectorsearch)}
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

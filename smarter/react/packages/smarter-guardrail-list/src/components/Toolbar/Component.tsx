/**
 * Toolbar React Component
 *
 * This component provides a toolbar for managing guardrail resources, used in both ListView and CardView displays.
 * It offers actions for opening, editing, cloning, renaming, and deleting a guardrail, with modal dialogs for confirmation and error handling.
 *
 * Features:
 * - Action buttons for: Open (chat), Edit (YAML manifest), Clone, Rename, and Delete guardrail resources.
 * - Modal dialogs for clone, rename, delete, error, and confirmation workflows.
 * - Ensures only one modal is open at a time for clear user interaction.
 * - Handles API calls for clone, rename, and delete operations, with feedback on success or failure.
 * - Accessible with ARIA labels and keyboard navigation.
 *
 * Props:
 * - sessionContext (SessionContext): Contains authentication and API information for backend operations.
 * - guardrail (Guardrail): The guardrail resource to manage.
 *
 * Usage:
 * <Toolbar sessionContext={sessionContext} guardrail={guardrail} />
 *
 * This component is intended to be embedded in each guardrail row or card in ListView and CardView.
 */
import { useState } from "react";
import type { SessionContext } from "@smarter/common";
import { fetchDjangoUrl, Modal } from "@smarter/common";

import { loggerPrefix } from "@/lib/const";
import type { Guardrail } from "@/lib/Types";

interface ToolbarProps {
  sessionContext: SessionContext;
  guardrail: Guardrail;
  onRequery: () => void;
}

export const Toolbar = ({ sessionContext, guardrail, onRequery }: ToolbarProps) => {
  // this is a single way to control which and whether a modal is open.
  // it ensures that only one modal can be open at a time, and simplifies
  // the logic for opening and closing any of the four modals.
  // url: string, csrfToken: string, djangoSessionCookieName: string, csrfCookieName: string, cookieDomain: string
  const [modal, setModal] = useState<{
    type: null | "clone" | "rename" | "delete" | "confirmation" | "error";
    guardrail: Guardrail | null;
  }>({ type: null, guardrail: null });
  const [errMessage, setErrMessage] = useState<string>("");
  const [successMessage, setSuccessMessage] = useState<string>("");

  const handleCloseModal = () => {
    setModal({ type: null, guardrail: null });
  };
  const handleCloseModalWithRequery = () => {
    setModal({ type: null, guardrail: null });
    onRequery();
  };

  const handleCloneButtonClicked = (guardrail: Guardrail) => setModal({ type: "clone", guardrail });
  const handleRenameButtonClicked = (guardrail: Guardrail) => setModal({ type: "rename", guardrail });
  const handleDeleteButtonClicked = (guardrail: Guardrail) => setModal({ type: "delete", guardrail });

  const handleError = (guardrail: Guardrail) => {
    handleCloseModal();
    setModal({ type: "error", guardrail });
  };

  const ModalClone = () => {
    const [inputValue, setInputValue] = useState("");
    return (
      <>
        <Modal
          show={modal.type === "clone"}
          title="Clone Guardrail"
          onOk={() => handleCloneGuardrail(modal.guardrail!, inputValue)}
          onCancel={handleCloseModal}
        >
          <p>
            Clone guardrail <strong>{modal.guardrail?.name}</strong> to a new resource owned by you.
          </p>
          <p>
            <em>Provide the new name for the cloned guardrail.</em>
          </p>
          <input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Enter new guardrail name"
          />
        </Modal>
      </>
    );
  };

  const ModalRename = () => {
    const [inputValue, setInputValue] = useState(modal.guardrail?.name || "");
    return (
      <>
        <Modal
          show={modal.type === "rename"}
          title="Rename Guardrail"
          onOk={() => handleRenameGuardrail(modal.guardrail!, inputValue)}
          onCancel={handleCloseModal}
        >
          <p>
            Rename guardrail <strong>{modal.guardrail?.name}</strong>.
          </p>
          <p>
            <em>Provide the new name for the guardrail.</em>
          </p>
          <input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Enter new guardrail name"
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
          title="Delete Guardrail"
          onOk={() => handleDeleteGuardrail(modal.guardrail!)}
          onCancel={handleCloseModal}
        >
          <p>
            Are you sure you want to delete guardrail <strong>{modal.guardrail?.name}</strong>?
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
            An error occurred while performing the operation on guardrail <strong>{modal.guardrail?.name}</strong>.
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
            {successMessage} <strong>{modal.guardrail?.name}</strong>.
          </p>
          <p>
            <em>Operation completed successfully.</em>
          </p>
        </Modal>
      </>
    );
  };

  const handleCloneGuardrail = async (guardrail: Guardrail, new_name: string) => {
    // see: smarter.apps.guardrail.urls for API urls
    // path("api/clone/<int:guardrail_id>/<str:new_name>/", GuardrailListApiCloneView.as_view(), name=GuardrailReverseNames.listview_api_clone),
    //
    // implement the clone logic here, e.g. call an API route to perform the clone operation.
    // return a success or failure result.

    const url = sessionContext.ApiUrl + "clone/" + guardrail.id + "/" + new_name + "/";
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
              throw new Error(`Failed to clone guardrail (${response.status}): ${errorMessage}`);
            })
            .catch(() => {
              throw new Error(`Failed to clone guardrail (${response.status}): ${response.statusText}`);
            });
        }
        return response.json();
      })
      .then((data: Guardrail) => {
        console.debug(loggerPrefix, "Successfully cloned guardrail:", data);
        setModal({ type: "confirmation", guardrail: data as Guardrail });
        setSuccessMessage(`Successfully cloned guardrail`);
      })
      .catch((error) => {
        console.error(loggerPrefix, "Error cloning guardrail:", error);
        setErrMessage(error.message);
        handleError(guardrail);
      });
    return true;
  };

  const handleRenameGuardrail = async (guardrail: Guardrail, newName: string) => {
    // implement the rename logic here, e.g. call an API route to perform the rename operation.
    // return a success or failure result.
    handleCloseModal();
    const url = sessionContext.ApiUrl + "rename/" + guardrail.id + "/" + newName + "/";

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
              throw new Error(`Failed to rename guardrail (${response.status}): ${errorMessage}`);
            })
            .catch(() => {
              throw new Error(`Failed to rename guardrail (${response.status}): ${response.statusText}`);
            });
        }
        return response.json();
      })
      .then((data: Guardrail) => {
        console.debug(loggerPrefix, "Successfully renamed guardrail:", data);
        setModal({ type: "confirmation", guardrail: data as Guardrail });
        setSuccessMessage(`Successfully renamed guardrail`);
      })
      .catch((error) => {
        console.error(loggerPrefix, "Error renaming guardrail:", error);
        setErrMessage(error.message);
        handleError(guardrail);
      });
    return true;
  };

  const handleDeleteGuardrail = async (guardrail: Guardrail) => {
    // implement the delete logic here, e.g. call an API route to perform the delete operation.
    // return a success or failure result.
    handleCloseModal();
    const url = sessionContext.ApiUrl + "delete/" + guardrail.id + "/";
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
              throw new Error(`Failed to delete guardrail (${response.status}): ${errorMessage}`);
            })
            .catch(() => {
              throw new Error(`Failed to delete guardrail (${response.status}): ${response.statusText}`);
            });
        }
        return response.json();
      })
      .then(() => {
        console.debug(loggerPrefix, "Successfully deleted guardrail:", guardrail);
        setModal({ type: "confirmation", guardrail });
        setSuccessMessage(`Successfully deleted guardrail`);
      })
      .catch((error) => {
        console.error(loggerPrefix, "Error deleting guardrail:", error);
        setErrMessage(error.message);
        handleError(guardrail);
      });
    return true;
  };

  return (
    <>
      <div className="toolbar btn-group pe-2" role="group" aria-label="Actions">
        <a
          href={guardrail.manifestUrl}
          className="btn btn-icon btn-sm border"
          title="Chat: Open the guardrail workbench"
          tabIndex={0}
        >
          <i className="bi bi-chat-dots" />
        </a>
        <a
          href={guardrail.manifestUrl}
          className="btn btn-icon btn-sm border"
          title="Edit: Open the YAML manifest that defines this guardrail resource"
          tabIndex={0}
        >
          <i className="bi bi-pencil-square" />
        </a>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Clone: Clone this guardrail resource to a new resource owned by you"
          onClick={() => handleCloneButtonClicked(guardrail)}
          tabIndex={0}
        >
          <i className="bi bi-files" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Rename: Rename this guardrail resource"
          onClick={() => handleRenameButtonClicked(guardrail)}
          tabIndex={0}
        >
          <i className="bi bi-pencil" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Delete: Delete this guardrail resource"
          onClick={() => handleDeleteButtonClicked(guardrail)}
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

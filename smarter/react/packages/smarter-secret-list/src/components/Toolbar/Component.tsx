/**
 * Toolbar React Component
 *
 * This component provides a toolbar for managing secret resources, used in both ListView and CardView displays.
 * It offers actions for opening, editing, cloning, renaming, and deleting a secret, with modal dialogs for confirmation and error handling.
 *
 * Features:
 * - Action buttons for: Open (chat), Edit (YAML manifest), Clone, Rename, and Delete secret resources.
 * - Modal dialogs for clone, rename, delete, error, and confirmation workflows.
 * - Ensures only one modal is open at a time for clear user interaction.
 * - Handles API calls for clone, rename, and delete operations, with feedback on success or failure.
 * - Accessible with ARIA labels and keyboard navigation.
 *
 * Props:
 * - sessionContext (SessionContext): Contains authentication and API information for backend operations.
 * - secret (Secret): The secret resource to manage.
 *
 * Usage:
 * <Toolbar sessionContext={sessionContext} secret={secret} />
 *
 * This component is intended to be embedded in each secret row or card in ListView and CardView.
 */
import { useState } from "react";
import type { SessionContext } from "@smarter/common";
import { fetchDjangoUrl, Modal } from "@smarter/common";

import { loggerPrefix } from "@/lib/const";
import type { Secret } from "@/lib/Types";

interface ToolbarProps {
  sessionContext: SessionContext;
  secret: Secret;
  onRequery: () => void;
}

export const Toolbar = ({ sessionContext, secret, onRequery }: ToolbarProps) => {
  // this is a single way to control which and whether a modal is open.
  // it ensures that only one modal can be open at a time, and simplifies
  // the logic for opening and closing any of the four modals.
  // url: string, csrfToken: string, djangoSessionCookieName: string, csrfCookieName: string, cookieDomain: string
  const [modal, setModal] = useState<{
    type: null | "clone" | "rename" | "delete" | "confirmation" | "error";
    secret: Secret | null;
  }>({ type: null, secret: null });
  const [errMessage, setErrMessage] = useState<string>("");
  const [successMessage, setSuccessMessage] = useState<string>("");

  const handleCloseModal = () => {
    setModal({ type: null, secret: null });
  };
  const handleCloseModalWithRequery = () => {
    setModal({ type: null, secret: null });
    onRequery();
  };

  const handleCloneButtonClicked = (secret: Secret) => setModal({ type: "clone", secret });
  const handleRenameButtonClicked = (secret: Secret) => setModal({ type: "rename", secret });
  const handleDeleteButtonClicked = (secret: Secret) => setModal({ type: "delete", secret });

  const handleError = (secret: Secret) => {
    handleCloseModal();
    setModal({ type: "error", secret });
  };

  const ModalClone = () => {
    const [inputValue, setInputValue] = useState("");
    return (
      <>
        <Modal
          show={modal.type === "clone"}
          title="Clone Secret"
          onOk={() => handleCloneSecret(modal.secret!, inputValue)}
          onCancel={handleCloseModal}
        >
          <p>
            Clone secret <strong>{modal.secret?.name}</strong> to a new resource owned by you.
          </p>
          <p>
            <em>Provide the new name for the cloned secret.</em>
          </p>
          <input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Enter new secret name"
          />
        </Modal>
      </>
    );
  };

  const ModalRename = () => {
    const [inputValue, setInputValue] = useState(modal.secret?.name || "");
    return (
      <>
        <Modal
          show={modal.type === "rename"}
          title="Rename Secret"
          onOk={() => handleRenameSecret(modal.secret!, inputValue)}
          onCancel={handleCloseModal}
        >
          <p>
            Rename secret <strong>{modal.secret?.name}</strong>.
          </p>
          <p>
            <em>Provide the new name for the secret.</em>
          </p>
          <input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Enter new secret name"
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
          title="Delete Secret"
          onOk={() => handleDeleteSecret(modal.secret!)}
          onCancel={handleCloseModal}
        >
          <p>
            Are you sure you want to delete secret <strong>{modal.secret?.name}</strong>?
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
            An error occurred while performing the operation on secret <strong>{modal.secret?.name}</strong>.
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
            {successMessage} <strong>{modal.secret?.name}</strong>.
          </p>
          <p>
            <em>Operation completed successfully.</em>
          </p>
        </Modal>
      </>
    );
  };

  const handleCloneSecret = async (secret: Secret, new_name: string) => {
    // see: smarter.apps.secret.urls for API urls
    // path("api/clone/<int:secret_id>/<str:new_name>/", SecretListApiCloneView.as_view(), name=SecretReverseNames.listview_api_clone),
    //
    // implement the clone logic here, e.g. call an API route to perform the clone operation.
    // return a success or failure result.

    const url = sessionContext.ApiUrl + "clone/" + secret.id + "/" + new_name + "/";
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
              throw new Error(`Failed to clone secret (${response.status}): ${errorMessage}`);
            })
            .catch(() => {
              throw new Error(`Failed to clone secret (${response.status}): ${response.statusText}`);
            });
        }
        return response.json();
      })
      .then((data: Secret) => {
        console.debug(loggerPrefix, "Successfully cloned secret:", data);
        setModal({ type: "confirmation", secret: data as Secret });
        setSuccessMessage(`Successfully cloned secret`);
      })
      .catch((error) => {
        console.error(loggerPrefix, "Error cloning secret:", error);
        setErrMessage(error.message);
        handleError(secret);
      });
    return true;
  };

  const handleRenameSecret = async (secret: Secret, newName: string) => {
    // implement the rename logic here, e.g. call an API route to perform the rename operation.
    // return a success or failure result.
    handleCloseModal();
    const url = sessionContext.ApiUrl + "rename/" + secret.id + "/" + newName + "/";

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
              throw new Error(`Failed to rename secret (${response.status}): ${errorMessage}`);
            })
            .catch(() => {
              throw new Error(`Failed to rename secret (${response.status}): ${response.statusText}`);
            });
        }
        return response.json();
      })
      .then((data: Secret) => {
        console.debug(loggerPrefix, "Successfully renamed secret:", data);
        setModal({ type: "confirmation", secret: data as Secret });
        setSuccessMessage(`Successfully renamed secret`);
      })
      .catch((error) => {
        console.error(loggerPrefix, "Error renaming secret:", error);
        setErrMessage(error.message);
        handleError(secret);
      });
    return true;
  };

  const handleDeleteSecret = async (secret: Secret) => {
    // implement the delete logic here, e.g. call an API route to perform the delete operation.
    // return a success or failure result.
    handleCloseModal();
    const url = sessionContext.ApiUrl + "delete/" + secret.id + "/";
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
              throw new Error(`Failed to delete secret (${response.status}): ${errorMessage}`);
            })
            .catch(() => {
              throw new Error(`Failed to delete secret (${response.status}): ${response.statusText}`);
            });
        }
        return response.json();
      })
      .then(() => {
        console.debug(loggerPrefix, "Successfully deleted secret:", secret);
        setModal({ type: "confirmation", secret });
        setSuccessMessage(`Successfully deleted secret`);
      })
      .catch((error) => {
        console.error(loggerPrefix, "Error deleting secret:", error);
        setErrMessage(error.message);
        handleError(secret);
      });
    return true;
  };

  return (
    <>
      <div className="toolbar btn-group pe-2" role="group" aria-label="Actions">
        <a
          href={secret.manifestUrl}
          className="btn btn-icon btn-sm border"
          title="Chat: Open the secret workbench"
          tabIndex={0}
        >
          <i className="bi bi-chat-dots" />
        </a>
        <a
          href={secret.manifestUrl}
          className="btn btn-icon btn-sm border"
          title="Edit: Open the YAML manifest that defines this secret resource"
          tabIndex={0}
        >
          <i className="bi bi-pencil-square" />
        </a>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Clone: Clone this secret resource to a new resource owned by you"
          onClick={() => handleCloneButtonClicked(secret)}
          tabIndex={0}
        >
          <i className="bi bi-files" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Rename: Rename this secret resource"
          onClick={() => handleRenameButtonClicked(secret)}
          tabIndex={0}
        >
          <i className="bi bi-pencil" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Delete: Delete this secret resource"
          onClick={() => handleDeleteButtonClicked(secret)}
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

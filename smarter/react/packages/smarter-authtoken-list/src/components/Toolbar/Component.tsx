/**
 * Toolbar React Component
 *
 * This component provides a toolbar for managing authtoken resources, used in both ListView and CardView displays.
 * It offers actions for opening, editing, cloning, renaming, and deleting a authtoken, with modal dialogs for confirmation and error handling.
 *
 * Features:
 * - Action buttons for: Open (chat), Edit (YAML manifest), Clone, Rename, and Delete authtoken resources.
 * - Modal dialogs for clone, rename, delete, error, and confirmation workflows.
 * - Ensures only one modal is open at a time for clear user interaction.
 * - Handles API calls for clone, rename, and delete operations, with feedback on success or failure.
 * - Accessible with ARIA labels and keyboard navigation.
 *
 * Props:
 * - sessionContext (SessionContext): Contains authentication and API information for backend operations.
 * - authtoken (AuthToken): The authtoken resource to manage.
 *
 * Usage:
 * <Toolbar sessionContext={sessionContext} authtoken={authtoken} />
 *
 * This component is intended to be embedded in each authtoken row or card in ListView and CardView.
 */
import { useState } from "react";

import type { SessionContext } from "@smarter/common";
import { Modal } from "@smarter/common";
import { fetchDjangoUrl } from "@smarter/common";

import { loggerPrefix } from "@/lib/const";
import type { AuthToken } from "@/lib/Types";

interface ToolbarProps {
  sessionContext: SessionContext;
  authtoken: AuthToken;
  onRequery: () => void;
}

export const Toolbar = ({ sessionContext, authtoken, onRequery }: ToolbarProps) => {
  // this is a single way to control which and whether a modal is open.
  // it ensures that only one modal can be open at a time, and simplifies
  // the logic for opening and closing any of the four modals.
  // url: string, csrfToken: string, djangoSessionCookieName: string, csrfCookieName: string, cookieDomain: string
  const [modal, setModal] = useState<{
    type: null | "clone" | "rename" | "delete" | "confirmation" | "error";
    authtoken: AuthToken | null;
  }>({ type: null, authtoken: null });
  const [errMessage, setErrMessage] = useState<string>("");
  const [successMessage, setSuccessMessage] = useState<string>("");

  const handleCloseModal = () => {
    setModal({ type: null, authtoken: null });
  };
  const handleCloseModalWithRequery = () => {
    setModal({ type: null, authtoken: null });
    onRequery();
  };

  const handleCloneButtonClicked = (authtoken: AuthToken) => setModal({ type: "clone", authtoken });
  const handleRenameButtonClicked = (authtoken: AuthToken) => setModal({ type: "rename", authtoken });
  const handleDeleteButtonClicked = (authtoken: AuthToken) => setModal({ type: "delete", authtoken });

  const handleError = (authtoken: AuthToken) => {
    handleCloseModal();
    setModal({ type: "error", authtoken });
  };

  const ModalClone = () => {
    const [inputValue, setInputValue] = useState("");
    return (
      <>
        <Modal
          show={modal.type === "clone"}
          title="Clone AuthToken"
          onOk={() => handleCloneAuthToken(modal.authtoken!, inputValue)}
          onCancel={handleCloseModal}
        >
          <p>
            Clone authtoken <strong>{modal.authtoken?.name}</strong> to a new resource owned by you.
          </p>
          <p>
            <em>Provide the new name for the cloned authtoken.</em>
          </p>
          <input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Enter new authtoken name"
          />
        </Modal>
      </>
    );
  };

  const ModalRename = () => {
    const [inputValue, setInputValue] = useState(modal.authtoken?.name || "");
    return (
      <>
        <Modal
          show={modal.type === "rename"}
          title="Rename AuthToken"
          onOk={() => handleRenameAuthToken(modal.authtoken!, inputValue)}
          onCancel={handleCloseModal}
        >
          <p>
            Rename authtoken <strong>{modal.authtoken?.name}</strong>.
          </p>
          <p>
            <em>Provide the new name for the authtoken.</em>
          </p>
          <input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Enter new authtoken name"
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
          title="Delete AuthToken"
          onOk={() => handleDeleteAuthToken(modal.authtoken!)}
          onCancel={handleCloseModal}
        >
          <p>
            Are you sure you want to delete authtoken <strong>{modal.authtoken?.name}</strong>?
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
            An error occurred while performing the operation on authtoken <strong>{modal.authtoken?.name}</strong>.
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
            {successMessage} <strong>{modal.authtoken?.name}</strong>.
          </p>
          <p>
            <em>Operation completed successfully.</em>
          </p>
        </Modal>
      </>
    );
  };

  const handleCloneAuthToken = async (authtoken: AuthToken, new_name: string) => {
    // see: smarter.apps.authtoken.urls for API urls
    // path("api/clone/<int:authtoken_id>/<str:new_name>/", AuthTokenListApiCloneView.as_view(), name=AuthTokenReverseNames.listview_api_clone),
    //
    // implement the clone logic here, e.g. call an API route to perform the clone operation.
    // return a success or failure result.

    const url = sessionContext.ApiUrl + "clone/" + authtoken.id + "/" + new_name + "/";
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
              throw new Error(`Failed to clone authtoken (${response.status}): ${errorMessage}`);
            })
            .catch(() => {
              throw new Error(`Failed to clone authtoken (${response.status}): ${response.statusText}`);
            });
        }
        return response.json();
      })
      .then((data: AuthToken) => {
        console.debug(loggerPrefix, "Successfully cloned authtoken:", data);
        setModal({ type: "confirmation", authtoken: data as AuthToken });
        setSuccessMessage(`Successfully cloned authtoken`);
      })
      .catch((error) => {
        console.error(loggerPrefix, "Error cloning authtoken:", error);
        setErrMessage(error.message);
        handleError(authtoken);
      });
    return true;
  };

  const handleRenameAuthToken = async (authtoken: AuthToken, newName: string) => {
    // implement the rename logic here, e.g. call an API route to perform the rename operation.
    // return a success or failure result.
    handleCloseModal();
    const url = sessionContext.ApiUrl + "rename/" + authtoken.id + "/" + newName + "/";

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
              throw new Error(`Failed to rename authtoken (${response.status}): ${errorMessage}`);
            })
            .catch(() => {
              throw new Error(`Failed to rename authtoken (${response.status}): ${response.statusText}`);
            });
        }
        return response.json();
      })
      .then((data: AuthToken) => {
        console.debug(loggerPrefix, "Successfully renamed authtoken:", data);
        setModal({ type: "confirmation", authtoken: data as AuthToken });
        setSuccessMessage(`Successfully renamed authtoken`);
      })
      .catch((error) => {
        console.error(loggerPrefix, "Error renaming authtoken:", error);
        setErrMessage(error.message);
        handleError(authtoken);
      });
    return true;
  };

  const handleDeleteAuthToken = async (authtoken: AuthToken) => {
    // implement the delete logic here, e.g. call an API route to perform the delete operation.
    // return a success or failure result.
    handleCloseModal();
    const url = sessionContext.ApiUrl + "delete/" + authtoken.id + "/";
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
              throw new Error(`Failed to delete authtoken (${response.status}): ${errorMessage}`);
            })
            .catch(() => {
              throw new Error(`Failed to delete authtoken (${response.status}): ${response.statusText}`);
            });
        }
        return response.json();
      })
      .then(() => {
        console.debug(loggerPrefix, "Successfully deleted authtoken:", authtoken);
        setModal({ type: "confirmation", authtoken });
        setSuccessMessage(`Successfully deleted authtoken`);
      })
      .catch((error) => {
        console.error(loggerPrefix, "Error deleting authtoken:", error);
        setErrMessage(error.message);
        handleError(authtoken);
      });
    return true;
  };

  return (
    <>
      <div className="toolbar btn-group pe-2" role="group" aria-label="Actions">
        <a
          href={authtoken.manifestUrl}
          className="btn btn-icon btn-sm border"
          title="Chat: Open the authtoken workbench"
          tabIndex={0}
        >
          <i className="bi bi-chat-dots" />
        </a>
        <a
          href={authtoken.manifestUrl}
          className="btn btn-icon btn-sm border"
          title="Edit: Open the YAML manifest that defines this authtoken resource"
          tabIndex={0}
        >
          <i className="bi bi-pencil-square" />
        </a>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Clone: Clone this authtoken resource to a new resource owned by you"
          onClick={() => handleCloneButtonClicked(authtoken)}
          tabIndex={0}
        >
          <i className="bi bi-files" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Rename: Rename this authtoken resource"
          onClick={() => handleRenameButtonClicked(authtoken)}
          tabIndex={0}
        >
          <i className="bi bi-pencil" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Delete: Delete this authtoken resource"
          onClick={() => handleDeleteButtonClicked(authtoken)}
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

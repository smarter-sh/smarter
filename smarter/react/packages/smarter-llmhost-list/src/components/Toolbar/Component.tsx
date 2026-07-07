/**
 * Toolbar React Component
 *
 * This component provides a toolbar for managing llmhost resources, used in both ListView and CardView displays.
 * It offers actions for opening, editing, cloning, renaming, and deleting a llmhost, with modal dialogs for confirmation and error handling.
 *
 * Features:
 * - Action buttons for: Open (chat), Edit (YAML manifest), Clone, Rename, and Delete llmhost resources.
 * - Modal dialogs for clone, rename, delete, error, and confirmation workflows.
 * - Ensures only one modal is open at a time for clear user interaction.
 * - Handles API calls for clone, rename, and delete operations, with feedback on success or failure.
 * - Accessible with ARIA labels and keyboard navigation.
 *
 * Props:
 * - sessionContext (SessionContext): Contains authentication and API information for backend operations.
 * - llmhost (LLMHost): The llmhost resource to manage.
 *
 * Usage:
 * <Toolbar sessionContext={sessionContext} llmhost={llmhost} />
 *
 * This component is intended to be embedded in each llmhost row or card in ListView and CardView.
 */
import { useState } from "react";
import type { SessionContext } from "@smarter/common";
import { fetchDjangoUrl, Modal } from "@smarter/common";

import { loggerPrefix } from "@/lib/const";
import type { LLMHost } from "@/lib/Types";

interface ToolbarProps {
  sessionContext: SessionContext;
  llmhost: LLMHost;
  onRequery: () => void;
}

export const Toolbar = ({ sessionContext, llmhost, onRequery }: ToolbarProps) => {
  // this is a single way to control which and whether a modal is open.
  // it ensures that only one modal can be open at a time, and simplifies
  // the logic for opening and closing any of the four modals.
  // url: string, csrfToken: string, djangoSessionCookieName: string, csrfCookieName: string, cookieDomain: string
  const [modal, setModal] = useState<{
    type: null | "clone" | "rename" | "delete" | "confirmation" | "error";
    llmhost: LLMHost | null;
  }>({ type: null, llmhost: null });
  const [errMessage, setErrMessage] = useState<string>("");
  const [successMessage, setSuccessMessage] = useState<string>("");

  const handleCloseModal = () => {
    setModal({ type: null, llmhost: null });
  };
  const handleCloseModalWithRequery = () => {
    setModal({ type: null, llmhost: null });
    onRequery();
  };

  const handleCloneButtonClicked = (llmhost: LLMHost) => setModal({ type: "clone", llmhost });
  const handleRenameButtonClicked = (llmhost: LLMHost) => setModal({ type: "rename", llmhost });
  const handleDeleteButtonClicked = (llmhost: LLMHost) => setModal({ type: "delete", llmhost });

  const handleError = (llmhost: LLMHost) => {
    handleCloseModal();
    setModal({ type: "error", llmhost });
  };

  const ModalClone = () => {
    const [inputValue, setInputValue] = useState("");
    return (
      <>
        <Modal
          show={modal.type === "clone"}
          title="Clone LLMHost"
          onOk={() => handleCloneLLMHost(modal.llmhost!, inputValue)}
          onCancel={handleCloseModal}
        >
          <p>
            Clone llmhost <strong>{modal.llmhost?.name}</strong> to a new resource owned by you.
          </p>
          <p>
            <em>Provide the new name for the cloned llmhost.</em>
          </p>
          <input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Enter new llmhost name"
          />
        </Modal>
      </>
    );
  };

  const ModalRename = () => {
    const [inputValue, setInputValue] = useState(modal.llmhost?.name || "");
    return (
      <>
        <Modal
          show={modal.type === "rename"}
          title="Rename LLMHost"
          onOk={() => handleRenameLLMHost(modal.llmhost!, inputValue)}
          onCancel={handleCloseModal}
        >
          <p>
            Rename llmhost <strong>{modal.llmhost?.name}</strong>.
          </p>
          <p>
            <em>Provide the new name for the llmhost.</em>
          </p>
          <input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Enter new llmhost name"
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
          title="Delete LLMHost"
          onOk={() => handleDeleteLLMHost(modal.llmhost!)}
          onCancel={handleCloseModal}
        >
          <p>
            Are you sure you want to delete llmhost <strong>{modal.llmhost?.name}</strong>?
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
            An error occurred while performing the operation on llmhost <strong>{modal.llmhost?.name}</strong>.
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
            {successMessage} <strong>{modal.llmhost?.name}</strong>.
          </p>
          <p>
            <em>Operation completed successfully.</em>
          </p>
        </Modal>
      </>
    );
  };

  const handleCloneLLMHost = async (llmhost: LLMHost, new_name: string) => {
    // see: smarter.apps.llmhost.urls for API urls
    // path("api/clone/<int:llmhost_id>/<str:new_name>/", LLMHostListApiCloneView.as_view(), name=LLMHostReverseNames.listview_api_clone),
    //
    // implement the clone logic here, e.g. call an API route to perform the clone operation.
    // return a success or failure result.

    const url = sessionContext.ApiUrl + "clone/" + llmhost.id + "/" + new_name + "/";
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
              throw new Error(`Failed to clone llmhost (${response.status}): ${errorMessage}`);
            })
            .catch(() => {
              throw new Error(`Failed to clone llmhost (${response.status}): ${response.statusText}`);
            });
        }
        return response.json();
      })
      .then((data: LLMHost) => {
        console.debug(loggerPrefix, "Successfully cloned llmhost:", data);
        setModal({ type: "confirmation", llmhost: data as LLMHost });
        setSuccessMessage(`Successfully cloned llmhost`);
      })
      .catch((error) => {
        console.error(loggerPrefix, "Error cloning llmhost:", error);
        setErrMessage(error.message);
        handleError(llmhost);
      });
    return true;
  };

  const handleRenameLLMHost = async (llmhost: LLMHost, newName: string) => {
    // implement the rename logic here, e.g. call an API route to perform the rename operation.
    // return a success or failure result.
    handleCloseModal();
    const url = sessionContext.ApiUrl + "rename/" + llmhost.id + "/" + newName + "/";

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
              throw new Error(`Failed to rename llmhost (${response.status}): ${errorMessage}`);
            })
            .catch(() => {
              throw new Error(`Failed to rename llmhost (${response.status}): ${response.statusText}`);
            });
        }
        return response.json();
      })
      .then((data: LLMHost) => {
        console.debug(loggerPrefix, "Successfully renamed llmhost:", data);
        setModal({ type: "confirmation", llmhost: data as LLMHost });
        setSuccessMessage(`Successfully renamed llmhost`);
      })
      .catch((error) => {
        console.error(loggerPrefix, "Error renaming llmhost:", error);
        setErrMessage(error.message);
        handleError(llmhost);
      });
    return true;
  };

  const handleDeleteLLMHost = async (llmhost: LLMHost) => {
    // implement the delete logic here, e.g. call an API route to perform the delete operation.
    // return a success or failure result.
    handleCloseModal();
    const url = sessionContext.ApiUrl + "delete/" + llmhost.id + "/";
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
              throw new Error(`Failed to delete llmhost (${response.status}): ${errorMessage}`);
            })
            .catch(() => {
              throw new Error(`Failed to delete llmhost (${response.status}): ${response.statusText}`);
            });
        }
        return response.json();
      })
      .then(() => {
        console.debug(loggerPrefix, "Successfully deleted llmhost:", llmhost);
        setModal({ type: "confirmation", llmhost });
        setSuccessMessage(`Successfully deleted llmhost`);
      })
      .catch((error) => {
        console.error(loggerPrefix, "Error deleting llmhost:", error);
        setErrMessage(error.message);
        handleError(llmhost);
      });
    return true;
  };

  return (
    <>
      <div className="toolbar btn-group pe-2" role="group" aria-label="Actions">
        <a
          href={llmhost.manifestUrl}
          className="btn btn-icon btn-sm border"
          title="Chat: Open the llmhost workbench"
          tabIndex={0}
        >
          <i className="bi bi-chat-dots" />
        </a>
        <a
          href={llmhost.manifestUrl}
          className="btn btn-icon btn-sm border"
          title="Edit: Open the YAML manifest that defines this llmhost resource"
          tabIndex={0}
        >
          <i className="bi bi-pencil-square" />
        </a>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Clone: Clone this llmhost resource to a new resource owned by you"
          onClick={() => handleCloneButtonClicked(llmhost)}
          tabIndex={0}
        >
          <i className="bi bi-files" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Rename: Rename this llmhost resource"
          onClick={() => handleRenameButtonClicked(llmhost)}
          tabIndex={0}
        >
          <i className="bi bi-pencil" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Delete: Delete this llmhost resource"
          onClick={() => handleDeleteButtonClicked(llmhost)}
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

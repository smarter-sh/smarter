/**
 * Toolbar React Component
 *
 * This component provides a toolbar for managing llmclient resources, used in both ListView and CardView displays.
 * It offers actions for opening, editing, cloning, renaming, and deleting an llmclient, with modal dialogs for confirmation and error handling.
 *
 * Features:
 * - Action buttons for: Open (chat), Edit (YAML manifest), Clone, Rename, and Delete llmclient resources.
 * - Modal dialogs for clone, rename, delete, error, and confirmation workflows.
 * - Ensures only one modal is open at a time for clear user interaction.
 * - Handles API calls for clone, rename, and delete operations, with feedback on success or failure.
 * - Accessible with ARIA labels and keyboard navigation.
 *
 * Props:
 * - sessionContext (SessionContext): Contains authentication and API information for backend operations.
 * - llmclient (LLMClient): The llmclient resource to manage.
 *
 * Usage:
 * <Toolbar sessionContext={sessionContext} llmclient={llmclient} />
 *
 * This component is intended to be embedded in each llmclient row or card in ListView and CardView.
 */
import { useState } from "react";
import type { SessionContext } from "@smarter/common";
import { fetchDjangoUrl, Modal } from "@smarter/common";

import { loggerPrefix } from "@/const";
import type { LLMClient } from "@/lib/Types";

interface ToolbarProps {
  sessionContext: SessionContext;
  llmclient: LLMClient;
  onRequery: () => void;
}

export const Toolbar = ({ sessionContext, llmclient, onRequery }: ToolbarProps) => {
  // this is a single way to control which and whether a modal is open.
  // it ensures that only one modal can be open at a time, and simplifies
  // the logic for opening and closing any of the four modals.
  // url: string, csrfToken: string, djangoSessionCookieName: string, csrfCookieName: string, cookieDomain: string
  const [modal, setModal] = useState<{
    type: null | "clone" | "rename" | "delete" | "confirmation" | "error";
    llmclient: LLMClient | null;
  }>({ type: null, llmclient: null });
  const [errMessage, setErrMessage] = useState<string>("");
  const [successMessage, setSuccessMessage] = useState<string>("");

  const handleCloseModal = () => {
    setModal({ type: null, llmclient: null });
  };
  const handleCloseModalWithRequery = () => {
    setModal({ type: null, llmclient: null });
    onRequery();
  };

  const handleCloneButtonClicked = (llmclient: LLMClient) => setModal({ type: "clone", llmclient });
  const handleRenameButtonClicked = (llmclient: LLMClient) => setModal({ type: "rename", llmclient });
  const handleDeleteButtonClicked = (llmclient: LLMClient) => setModal({ type: "delete", llmclient });

  const handleError = (llmclient: LLMClient) => {
    handleCloseModal();
    setModal({ type: "error", llmclient });
  };

  const ModalClone = () => {
    const [inputValue, setInputValue] = useState("");
    return (
      <>
        <Modal
          show={modal.type === "clone"}
          title="Clone LLMClient"
          onOk={() => handleCloneLLMClient(modal.llmclient!, inputValue)}
          onCancel={handleCloseModal}
        >
          <p>
            Clone llmclient <strong>{modal.llmclient?.name}</strong> to a new resource owned by you.
          </p>
          <p>
            <em>Provide the new name for the cloned llmclient.</em>
          </p>
          <input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Enter new llmclient name"
          />
        </Modal>
      </>
    );
  };

  const ModalRename = () => {
    const [inputValue, setInputValue] = useState(modal.llmclient?.name || "");
    return (
      <>
        <Modal
          show={modal.type === "rename"}
          title="Rename LLMClient"
          onOk={() => handleRenameLLMClient(modal.llmclient!, inputValue)}
          onCancel={handleCloseModal}
        >
          <p>
            Rename llmclient <strong>{modal.llmclient?.name}</strong>.
          </p>
          <p>
            <em>Provide the new name for the llmclient.</em>
          </p>
          <input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Enter new llmclient name"
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
          title="Delete LLMClient"
          onOk={() => handleDeleteLLMClient(modal.llmclient!)}
          onCancel={handleCloseModal}
        >
          <p>
            Are you sure you want to delete llmclient <strong>{modal.llmclient?.name}</strong>?
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
            An error occurred while performing the operation on llmclient <strong>{modal.llmclient?.name}</strong>.
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
            {successMessage} <strong>{modal.llmclient?.name}</strong>.
          </p>
          <p>
            <em>Operation completed successfully.</em>
          </p>
        </Modal>
      </>
    );
  };

  const handleCloneLLMClient = async (llmclient: LLMClient, new_name: string) => {
    // see: smarter.apps.prompt.urls for API urls
    // path("api/clone/<int:llmclient_id>/<str:new_name>/", PromptListApiCloneView.as_view(), name=PromptReverseNames.listview_api_clone),
    //
    // implement the clone logic here, e.g. call an API route to perform the clone operation.
    // return a success or failure result.

    const url = sessionContext.ApiUrl + "clone/" + llmclient.id + "/" + new_name + "/";
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
              throw new Error(`Failed to clone llmclient (${response.status}): ${errorMessage}`);
            })
            .catch(() => {
              throw new Error(`Failed to clone llmclient (${response.status}): ${response.statusText}`);
            });
        }
        return response.json();
      })
      .then((data: LLMClient) => {
        console.debug(loggerPrefix, "Successfully cloned llmclient:", data);
        setModal({ type: "confirmation", llmclient: data as LLMClient });
        setSuccessMessage(`Successfully cloned llmclient`);
      })
      .catch((error) => {
        console.error(loggerPrefix, "Error cloning llmclient:", error);
        setErrMessage(error.message);
        handleError(llmclient);
      });
    return true;
  };

  const handleRenameLLMClient = async (llmclient: LLMClient, newName: string) => {
    // implement the rename logic here, e.g. call an API route to perform the rename operation.
    // return a success or failure result.
    handleCloseModal();
    const url = sessionContext.ApiUrl + "rename/" + llmclient.id + "/" + newName + "/";

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
              throw new Error(`Failed to rename llmclient (${response.status}): ${errorMessage}`);
            })
            .catch(() => {
              throw new Error(`Failed to rename llmclient (${response.status}): ${response.statusText}`);
            });
        }
        return response.json();
      })
      .then((data: LLMClient) => {
        console.debug(loggerPrefix, "Successfully renamed llmclient:", data);
        setModal({ type: "confirmation", llmclient: data as LLMClient });
        setSuccessMessage(`Successfully renamed llmclient`);
      })
      .catch((error) => {
        console.error(loggerPrefix, "Error renaming llmclient:", error);
        setErrMessage(error.message);
        handleError(llmclient);
      });
    return true;
  };

  const handleDeleteLLMClient = async (llmclient: LLMClient) => {
    // implement the delete logic here, e.g. call an API route to perform the delete operation.
    // return a success or failure result.
    handleCloseModal();
    const url = sessionContext.ApiUrl + "delete/" + llmclient.id + "/";
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
              throw new Error(`Failed to delete llmclient (${response.status}): ${errorMessage}`);
            })
            .catch(() => {
              throw new Error(`Failed to delete llmclient (${response.status}): ${response.statusText}`);
            });
        }
        return response.json();
      })
      .then(() => {
        console.debug(loggerPrefix, "Successfully deleted llmclient:", llmclient);
        setModal({ type: "confirmation", llmclient });
        setSuccessMessage(`Successfully deleted llmclient`);
      })
      .catch((error) => {
        console.error(loggerPrefix, "Error deleting llmclient:", error);
        setErrMessage(error.message);
        handleError(llmclient);
      });
    return true;
  };

  return (
    <>
      <div className="toolbar btn-group pe-2" role="group" aria-label="Actions">
        <a
          href={llmclient.urlChatapp}
          className="btn btn-icon btn-sm border"
          title="Chat: Open the prompt workbench"
          tabIndex={0}
        >
          <i className="bi bi-chat-dots" />
        </a>
        <a
          href={llmclient.urlManifest}
          className="btn btn-icon btn-sm border"
          title="Edit: Open the YAML manifest that defines this llmclient resource"
          tabIndex={0}
        >
          <i className="bi bi-pencil-square" />
        </a>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Clone: Clone this llmclient resource to a new resource owned by you"
          onClick={() => handleCloneButtonClicked(llmclient)}
          tabIndex={0}
        >
          <i className="bi bi-files" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Rename: Rename this llmclient resource"
          onClick={() => handleRenameButtonClicked(llmclient)}
          tabIndex={0}
        >
          <i className="bi bi-pencil" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Delete: Delete this llmclient resource"
          onClick={() => handleDeleteButtonClicked(llmclient)}
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

/**
 * Toolbar React Component
 *
 * This component provides a toolbar for managing llm_client resources, used in both ListView and CardView displays.
 * It offers actions for opening, editing, cloning, renaming, and deleting an llm_client, with modal dialogs for confirmation and error handling.
 *
 * Features:
 * - Action buttons for: Open (chat), Edit (YAML manifest), Clone, Rename, and Delete llm_client resources.
 * - Modal dialogs for clone, rename, delete, error, and confirmation workflows.
 * - Ensures only one modal is open at a time for clear user interaction.
 * - Handles API calls for clone, rename, and delete operations, with feedback on success or failure.
 * - Accessible with ARIA labels and keyboard navigation.
 *
 * Props:
 * - sessionContext (SessionContext): Contains authentication and API information for backend operations.
 * - llm_client (LLMClient): The llm_client resource to manage.
 *
 * Usage:
 * <Toolbar sessionContext={sessionContext} llm_client={llm_client} />
 *
 * This component is intended to be embedded in each llm_client row or card in ListView and CardView.
 */
import { useState } from "react";
import { loggerPrefix } from "@/const";
import type { LLMClient, SessionContext } from "@/lib/Types";
import { Modal } from "@/lib/modalDialogue";
import fetchDjangoUrl from "@/lib/django";

interface ToolbarProps {
  sessionContext: SessionContext;
  llm_client: LLMClient;
  onRequery: () => void;
}

export const Toolbar = ({ sessionContext, llm_client, onRequery }: ToolbarProps) => {
  // this is a single way to control which and whether a modal is open.
  // it ensures that only one modal can be open at a time, and simplifies
  // the logic for opening and closing any of the four modals.
  // url: string, csrfToken: string, djangoSessionCookieName: string, csrfCookieName: string, cookieDomain: string
  const [modal, setModal] = useState<{
    type: null | "clone" | "rename" | "delete" | "confirmation" | "error";
    llm_client: LLMClient | null;
  }>({ type: null, llm_client: null });
  const [errMessage, setErrMessage] = useState<string>("");
  const [successMessage, setSuccessMessage] = useState<string>("");

  const handleCloseModal = () => {
    setModal({ type: null, llm_client: null });
  };
  const handleCloseModalWithRequery = () => {
    setModal({ type: null, llm_client: null });
    onRequery();
  };

  const handleCloneButtonClicked = (llm_client: LLMClient) => setModal({ type: "clone", llm_client });
  const handleRenameButtonClicked = (llm_client: LLMClient) => setModal({ type: "rename", llm_client });
  const handleDeleteButtonClicked = (llm_client: LLMClient) => setModal({ type: "delete", llm_client });

  const handleError = (llm_client: LLMClient) => {
    handleCloseModal();
    setModal({ type: "error", llm_client });
  };

  const ModalClone = () => {
    const [inputValue, setInputValue] = useState("");
    return (
      <>
        <Modal
          show={modal.type === "clone"}
          title="Clone LLMClient"
          onOk={() => handleCloneLLMClient(modal.llm_client!, inputValue)}
          onCancel={handleCloseModal}
        >
          <p>
            Clone llm_client <strong>{modal.llm_client?.name}</strong> to a new resource owned by you.
          </p>
          <p>
            <em>Provide the new name for the cloned llm_client.</em>
          </p>
          <input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Enter new llm_client name"
          />
        </Modal>
      </>
    );
  };

  const ModalRename = () => {
    const [inputValue, setInputValue] = useState(modal.llm_client?.name || "");
    return (
      <>
        <Modal
          show={modal.type === "rename"}
          title="Rename LLMClient"
          onOk={() => handleRenameLLMClient(modal.llm_client!, inputValue)}
          onCancel={handleCloseModal}
        >
          <p>
            Rename llm_client <strong>{modal.llm_client?.name}</strong>.
          </p>
          <p>
            <em>Provide the new name for the llm_client.</em>
          </p>
          <input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Enter new llm_client name"
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
          onOk={() => handleDeleteLLMClient(modal.llm_client!)}
          onCancel={handleCloseModal}
        >
          <p>
            Are you sure you want to delete llm_client <strong>{modal.llm_client?.name}</strong>?
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
            An error occurred while performing the operation on llm_client <strong>{modal.llm_client?.name}</strong>.
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
            {successMessage} <strong>{modal.llm_client?.name}</strong>.
          </p>
          <p>
            <em>Operation completed successfully.</em>
          </p>
        </Modal>
      </>
    );
  };

  const handleCloneLLMClient = async (llm_client: LLMClient, new_name: string) => {
    // see: smarter.apps.prompt.urls for API urls
    // path("api/clone/<int:llm_client_id>/<str:new_name>/", PromptListApiCloneView.as_view(), name=PromptReverseNames.listview_api_clone),
    //
    // implement the clone logic here, e.g. call an API route to perform the clone operation.
    // return a success or failure result.

    const url = sessionContext.ApiUrl + "clone/" + llm_client.id + "/" + new_name + "/";
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
              throw new Error(`Failed to clone llm_client (${response.status}): ${errorMessage}`);
            })
            .catch(() => {
              throw new Error(`Failed to clone llm_client (${response.status}): ${response.statusText}`);
            });
        }
        return response.json();
      })
      .then((data: LLMClient) => {
        console.debug(loggerPrefix, "Successfully cloned llm_client:", data);
        setModal({ type: "confirmation", llm_client: data as LLMClient });
        setSuccessMessage(`Successfully cloned llm_client`);
      })
      .catch((error) => {
        console.error(loggerPrefix, "Error cloning llm_client:", error);
        setErrMessage(error.message);
        handleError(llm_client);
      });
    return true;
  };

  const handleRenameLLMClient = async (llm_client: LLMClient, newName: string) => {
    // implement the rename logic here, e.g. call an API route to perform the rename operation.
    // return a success or failure result.
    handleCloseModal();
    const url = sessionContext.ApiUrl + "rename/" + llm_client.id + "/" + newName + "/";

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
              throw new Error(`Failed to rename llm_client (${response.status}): ${errorMessage}`);
            })
            .catch(() => {
              throw new Error(`Failed to rename llm_client (${response.status}): ${response.statusText}`);
            });
        }
        return response.json();
      })
      .then((data: LLMClient) => {
        console.debug(loggerPrefix, "Successfully renamed llm_client:", data);
        setModal({ type: "confirmation", llm_client: data as LLMClient });
        setSuccessMessage(`Successfully renamed llm_client`);
      })
      .catch((error) => {
        console.error(loggerPrefix, "Error renaming llm_client:", error);
        setErrMessage(error.message);
        handleError(llm_client);
      });
    return true;
  };

  const handleDeleteLLMClient = async (llm_client: LLMClient) => {
    // implement the delete logic here, e.g. call an API route to perform the delete operation.
    // return a success or failure result.
    handleCloseModal();
    const url = sessionContext.ApiUrl + "delete/" + llm_client.id + "/";
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
              throw new Error(`Failed to delete llm_client (${response.status}): ${errorMessage}`);
            })
            .catch(() => {
              throw new Error(`Failed to delete llm_client (${response.status}): ${response.statusText}`);
            });
        }
        return response.json();
      })
      .then(() => {
        console.debug(loggerPrefix, "Successfully deleted llm_client:", llm_client);
        setModal({ type: "confirmation", llm_client });
        setSuccessMessage(`Successfully deleted llm_client`);
      })
      .catch((error) => {
        console.error(loggerPrefix, "Error deleting llm_client:", error);
        setErrMessage(error.message);
        handleError(llm_client);
      });
    return true;
  };

  return (
    <>
      <div className="toolbar btn-group pe-2" role="group" aria-label="Actions">
        <a
          href={llm_client.urlChatapp}
          className="btn btn-icon btn-sm border"
          title="Chat: Open the prompt workbench"
          tabIndex={0}
        >
          <i className="bi bi-chat-dots" />
        </a>
        <a
          href={llm_client.urlManifest}
          className="btn btn-icon btn-sm border"
          title="Edit: Open the YAML manifest that defines this llm_client resource"
          tabIndex={0}
        >
          <i className="bi bi-pencil-square" />
        </a>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Clone: Clone this llm_client resource to a new resource owned by you"
          onClick={() => handleCloneButtonClicked(llm_client)}
          tabIndex={0}
        >
          <i className="bi bi-files" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Rename: Rename this llm_client resource"
          onClick={() => handleRenameButtonClicked(llm_client)}
          tabIndex={0}
        >
          <i className="bi bi-pencil" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Delete: Delete this llm_client resource"
          onClick={() => handleDeleteButtonClicked(llm_client)}
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

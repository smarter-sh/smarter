import { useState } from "react";
import type { Chatbot } from "@/lib/Types";
import { Modal } from "@/lib/modalDialogue";
import fetchDjangoUrl from "@/lib/django";
import type { SessionContext } from "@/lib/Types";

interface ToolbarProps {
  sessionContext: SessionContext;
  chatbot: Chatbot;
}

export const Toolbar = ({ sessionContext, chatbot }: ToolbarProps) => {
  // this is a single way to control which and whether a modal is open.
  // it ensures that only one modal can be open at a time, and simplifies
  // the logic for opening and closing any of the four modals.
  // url: string, csrfToken: string, djangoSessionCookieName: string, csrfCookieName: string, cookieDomain: string
  const [modal, setModal] = useState<{
    type: null | "clone" | "rename" | "delete" | "confirmation" | "error";
    chatbot: Chatbot | null;
  }>({ type: null, chatbot: null });
  const [errMessage, setErrMessage] = useState<string>("");
  const [successMessage, setSuccessMessage] = useState<string>("");

  const handleCloseModal = () => setModal({ type: null, chatbot: null });

  const handleError = (chatbot: Chatbot) => {
    // open the error modal for this chatbot
    handleCloseModal();
    setModal({ type: "error", chatbot });
  };

  const handleCloneButtonClicked = (chatbot: Chatbot) => {
    // open the clone modal for this chatbot
    setModal({ type: "clone", chatbot });

    if (chatbot) {
      // do the clone operation.
      return;
      // on success, close the modal and navigate and refresh the page.
    }

    // on failure, show the error modal
    handleError(chatbot);
  };

  const handleRenameButtonClicked = (chatbot: Chatbot) => {
    // open the rename modal for this chatbot
    setModal({ type: "rename", chatbot });

    if (chatbot) {
      // do the rename operation.
      return;
      // on success, close the modal and navigate and refresh the page.
    }
    // on failure, show the error modal
    handleError(chatbot);
  };

  const handleDeleteButtonClicked = (chatbot: Chatbot) => {
    // open the delete modal for this chatbot
    setModal({ type: "delete", chatbot });

    if (chatbot) {
      // do the delete operation.
      return;
      // on success, close the modal and navigate and refresh the page.
    }
    // on failure, show the error modal
    handleError(chatbot);
  };

  const ModalClone = () => {
    const [inputValue, setInputValue] = useState("");
    return (
      <>
        <Modal
          show={modal.type === "clone"}
          title="Clone Chatbot"
          onOk={() => handleCloneChatbot(modal.chatbot!, inputValue)}
          onCancel={handleCloseModal}
        >
          <p>
            Clone chatbot <strong>{modal.chatbot?.name}</strong> to a new
            resource owned by you.
          </p>
          <p>
            <em>Provide the new name for the cloned chatbot.</em>
          </p>
          <input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Enter new chatbot name"
          />
        </Modal>
      </>
    );
  };

  const ModalRename = () => {
    const [inputValue, setInputValue] = useState(modal.chatbot?.name || "");
    return (
      <>
        <Modal
          show={modal.type === "rename"}
          title="Rename Chatbot"
          onOk={() => handleRenameChatbot(modal.chatbot!, inputValue)}
          onCancel={handleCloseModal}
        >
          <p>
            Rename chatbot <strong>{modal.chatbot?.name}</strong>.
          </p>
          <p>
            <em>Provide the new name for the chatbot.</em>
          </p>
          <input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Enter new chatbot name"
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
          title="Delete Chatbot"
          onOk={() => handleDeleteChatbot(modal.chatbot!)}
          onCancel={handleCloseModal}
        >
          <p>
            Are you sure you want to delete chatbot{" "}
            <strong>{modal.chatbot?.name}</strong>?
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
        <Modal
          show={modal.type === "error"}
          title="❌ Error"
          onClose={handleCloseModal}
        >
          <p>
            An error occurred while performing the operation on chatbot{" "}
            <strong>{modal.chatbot?.name}</strong>.
          </p>
          <p>
            {errMessage ? (
              <span className="text-danger">{errMessage}</span>
            ) : (
              <em>An unknown error occurred.</em>
            )}
          </p>
        </Modal>
      </>
    );
  };

  const ModalConfirmation = () => {
    return (
      <>
        <Modal
          show={modal.type === "confirmation"}
          title="✅ Success"
          onClose={handleCloseModal}
        >
          <p>
            {successMessage}{" "}
            <strong>{modal.chatbot?.name}</strong>.
          </p>
          <p>
            <em>Operation completed successfully.</em>
          </p>
        </Modal>
      </>
    );
  };

  const handleCloneChatbot = async (chatbot: Chatbot, new_name: string) => {
    // see: smarter.apps.prompt.urls for API urls
    // path("api/clone/<int:chatbot_id>/<str:new_name>/", PromptListApiCloneView.as_view(), name=PromptReverseNames.listview_api_clone),
    //
    // implement the clone logic here, e.g. call an API route to perform the clone operation.
    // return a success or failure result.

    const url =
      sessionContext.myResourcesApiUrl +
      "clone/" +
      chatbot.id +
      "/" +
      new_name +
      "/";
    handleCloseModal();
    fetchDjangoUrl(
      JSON.stringify({}),
      url,
      sessionContext.csrftoken,
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
              throw new Error(
                `Failed to clone chatbot (${response.status}): ${errorMessage}`,
              );
            })
            .catch(() => {
              throw new Error(
                `Failed to clone chatbot (${response.status}): ${response.statusText}`,
              );
            });
        }
        return response.json();
      })
      .then((data: Chatbot) => {
        setModal({ type: "confirmation", chatbot: data as Chatbot });
        setSuccessMessage(`Successfully cloned chatbot`);
      })
      .catch((error) => {
        console.error("Error cloning chatbot:", error);
        setErrMessage(error.message);
        handleError(chatbot);
      });
    return true;
  };

  const handleRenameChatbot = async (chatbot: Chatbot, newName: string) => {
    // implement the rename logic here, e.g. call an API route to perform the rename operation.
    // return a success or failure result.
    handleCloseModal();
    fetchDjangoUrl(
      JSON.stringify({}),
      sessionContext.myResourcesApiUrl +
        "rename/" +
        chatbot.id +
        "/" +
        newName +
        "/",
      sessionContext.csrftoken,
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
              throw new Error(
                `Failed to rename chatbot (${response.status}): ${errorMessage}`,
              );
            })
            .catch(() => {
              throw new Error(
                `Failed to rename chatbot (${response.status}): ${response.statusText}`,
              );
            });
        }
        return response.json();
      })
      .then((data: Chatbot) => {
        setModal({ type: "confirmation", chatbot: data as Chatbot });
        setSuccessMessage(`Successfully renamed chatbot`);
      })
      .catch((error) => {
        console.error("Error renaming chatbot:", error);
        setErrMessage(error.message);
        handleError(chatbot);
      });
    return true;
  };

  const handleDeleteChatbot = async (chatbot: Chatbot) => {
    // implement the delete logic here, e.g. call an API route to perform the delete operation.
    // return a success or failure result.
    handleCloseModal();
    fetchDjangoUrl(
      JSON.stringify({}),
      sessionContext.myResourcesApiUrl + "delete/" + chatbot.id + "/",
      sessionContext.csrftoken,
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
              throw new Error(
                `Failed to delete chatbot (${response.status}): ${errorMessage}`,
              );
            })
            .catch(() => {
              throw new Error(
                `Failed to delete chatbot (${response.status}): ${response.statusText}`,
              );
            });
        }
        return response.json();
      })
      .then(() => {
        setModal({ type: "confirmation", chatbot });
        setSuccessMessage(`Successfully deleted chatbot`);
      })
      .catch((error) => {
        console.error("Error deleting chatbot:", error);
        setErrMessage(error.message);
        handleError(chatbot);
      });
    return true;
  };

  return (
    <>
      <div className="btn-group pe-2" role="group" aria-label="Actions">
        <a
          href={chatbot.urls.chat}
          className="btn btn-icon btn-sm border"
          title="Chat: Open the prompt workbench"
          tabIndex={0}
        >
          <i className="bi bi-chat-dots" />
        </a>
        <a
          href={chatbot.urls.manifest}
          className="btn btn-icon btn-sm border"
          title="Edit: Open the YAML manifest that defines this chatbot resource"
          tabIndex={0}
        >
          <i className="bi bi-pencil-square" />
        </a>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Clone: Clone this chatbot resource to a new resource owned by you"
          onClick={() => handleCloneButtonClicked(chatbot)}
          tabIndex={0}
        >
          <i className="bi bi-files" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Rename: Rename this chatbot resource"
          onClick={() => handleRenameButtonClicked(chatbot)}
          tabIndex={0}
        >
          <i className="bi bi-pencil" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Delete: Delete this chatbot resource"
          onClick={() => handleDeleteButtonClicked(chatbot)}
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

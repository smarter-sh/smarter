/**
 * Toolbar React Component
 *
 * This component provides a toolbar for managing provider resources, used in both ListView and CardView displays.
 * It offers actions for opening, editing, cloning, renaming, and deleting a provider, with modal dialogs for confirmation and error handling.
 *
 * Features:
 * - Action buttons for: Open (chat), Edit (YAML manifest), Clone, Rename, and Delete provider resources.
 * - Modal dialogs for clone, rename, delete, error, and confirmation workflows.
 * - Ensures only one modal is open at a time for clear user interaction.
 * - Handles API calls for clone, rename, and delete operations, with feedback on success or failure.
 * - Accessible with ARIA labels and keyboard navigation.
 *
 * Props:
 * - sessionContext (SessionContext): Contains authentication and API information for backend operations.
 * - provider (Provider): The provider resource to manage.
 *
 * Usage:
 * <Toolbar sessionContext={sessionContext} provider={provider} />
 *
 * This component is intended to be embedded in each provider row or card in ListView and CardView.
 */
import { useState } from "react";
import type { SessionContext } from "@smarter/common";
import { fetchDjangoUrl, Modal } from "@smarter/common";

import { loggerPrefix } from "@/lib/const";
import type { Provider } from "@/lib/Types";

interface ToolbarProps {
  sessionContext: SessionContext;
  provider: Provider;
  onRequery: () => void;
}

export const Toolbar = ({ sessionContext, provider, onRequery }: ToolbarProps) => {
  // this is a single way to control which and whether a modal is open.
  // it ensures that only one modal can be open at a time, and simplifies
  // the logic for opening and closing any of the four modals.
  // url: string, csrfToken: string, djangoSessionCookieName: string, csrfCookieName: string, cookieDomain: string
  const [modal, setModal] = useState<{
    type: null | "clone" | "rename" | "delete" | "confirmation" | "error";
    provider: Provider | null;
  }>({ type: null, provider: null });
  const [errMessage, setErrMessage] = useState<string>("");
  const [successMessage, setSuccessMessage] = useState<string>("");

  const handleCloseModal = () => {
    setModal({ type: null, provider: null });
  };
  const handleCloseModalWithRequery = () => {
    setModal({ type: null, provider: null });
    onRequery();
  };

  const handleCloneButtonClicked = (provider: Provider) => setModal({ type: "clone", provider });
  const handleRenameButtonClicked = (provider: Provider) => setModal({ type: "rename", provider });
  const handleDeleteButtonClicked = (provider: Provider) => setModal({ type: "delete", provider });

  const handleError = (provider: Provider) => {
    handleCloseModal();
    setModal({ type: "error", provider });
  };

  const ModalClone = () => {
    const [inputValue, setInputValue] = useState("");
    return (
      <>
        <Modal
          show={modal.type === "clone"}
          title="Clone Provider"
          onOk={() => handleCloneProvider(modal.provider!, inputValue)}
          onCancel={handleCloseModal}
        >
          <p>
            Clone provider <strong>{modal.provider?.name}</strong> to a new resource owned by you.
          </p>
          <p>
            <em>Provide the new name for the cloned provider.</em>
          </p>
          <input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Enter new provider name"
          />
        </Modal>
      </>
    );
  };

  const ModalRename = () => {
    const [inputValue, setInputValue] = useState(modal.provider?.name || "");
    return (
      <>
        <Modal
          show={modal.type === "rename"}
          title="Rename Provider"
          onOk={() => handleRenameProvider(modal.provider!, inputValue)}
          onCancel={handleCloseModal}
        >
          <p>
            Rename provider <strong>{modal.provider?.name}</strong>.
          </p>
          <p>
            <em>Provide the new name for the provider.</em>
          </p>
          <input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Enter new provider name"
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
          title="Delete Provider"
          onOk={() => handleDeleteProvider(modal.provider!)}
          onCancel={handleCloseModal}
        >
          <p>
            Are you sure you want to delete provider <strong>{modal.provider?.name}</strong>?
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
            An error occurred while performing the operation on provider <strong>{modal.provider?.name}</strong>.
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
            {successMessage} <strong>{modal.provider?.name}</strong>.
          </p>
          <p>
            <em>Operation completed successfully.</em>
          </p>
        </Modal>
      </>
    );
  };

  const handleCloneProvider = async (provider: Provider, new_name: string) => {
    // see: smarter.apps.provider.urls for API urls
    // path("api/clone/<int:provider_id>/<str:new_name>/", ProviderListApiCloneView.as_view(), name=ProviderReverseNames.listview_api_clone),
    //
    // implement the clone logic here, e.g. call an API route to perform the clone operation.
    // return a success or failure result.

    const url = sessionContext.ApiUrl + "clone/" + provider.id + "/" + new_name + "/";
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
              throw new Error(`Failed to clone provider (${response.status}): ${errorMessage}`);
            })
            .catch(() => {
              throw new Error(`Failed to clone provider (${response.status}): ${response.statusText}`);
            });
        }
        return response.json();
      })
      .then((data: Provider) => {
        console.debug(loggerPrefix, "Successfully cloned provider:", data);
        setModal({ type: "confirmation", provider: data as Provider });
        setSuccessMessage(`Successfully cloned provider`);
      })
      .catch((error) => {
        console.error(loggerPrefix, "Error cloning provider:", error);
        setErrMessage(error.message);
        handleError(provider);
      });
    return true;
  };

  const handleRenameProvider = async (provider: Provider, newName: string) => {
    // implement the rename logic here, e.g. call an API route to perform the rename operation.
    // return a success or failure result.
    handleCloseModal();
    const url = sessionContext.ApiUrl + "rename/" + provider.id + "/" + newName + "/";

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
              throw new Error(`Failed to rename provider (${response.status}): ${errorMessage}`);
            })
            .catch(() => {
              throw new Error(`Failed to rename provider (${response.status}): ${response.statusText}`);
            });
        }
        return response.json();
      })
      .then((data: Provider) => {
        console.debug(loggerPrefix, "Successfully renamed provider:", data);
        setModal({ type: "confirmation", provider: data as Provider });
        setSuccessMessage(`Successfully renamed provider`);
      })
      .catch((error) => {
        console.error(loggerPrefix, "Error renaming provider:", error);
        setErrMessage(error.message);
        handleError(provider);
      });
    return true;
  };

  const handleDeleteProvider = async (provider: Provider) => {
    // implement the delete logic here, e.g. call an API route to perform the delete operation.
    // return a success or failure result.
    handleCloseModal();
    const url = sessionContext.ApiUrl + "delete/" + provider.id + "/";
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
              throw new Error(`Failed to delete provider (${response.status}): ${errorMessage}`);
            })
            .catch(() => {
              throw new Error(`Failed to delete provider (${response.status}): ${response.statusText}`);
            });
        }
        return response.json();
      })
      .then(() => {
        console.debug(loggerPrefix, "Successfully deleted provider:", provider);
        setModal({ type: "confirmation", provider });
        setSuccessMessage(`Successfully deleted provider`);
      })
      .catch((error) => {
        console.error(loggerPrefix, "Error deleting provider:", error);
        setErrMessage(error.message);
        handleError(provider);
      });
    return true;
  };

  return (
    <>
      <div className="toolbar btn-group pe-2" role="group" aria-label="Actions">
        <a
          href={provider.manifestUrl}
          className="btn btn-icon btn-sm border"
          title="Chat: Open the provider workbench"
          tabIndex={0}
        >
          <i className="bi bi-chat-dots" />
        </a>
        <a
          href={provider.manifestUrl}
          className="btn btn-icon btn-sm border"
          title="Edit: Open the YAML manifest that defines this provider resource"
          tabIndex={0}
        >
          <i className="bi bi-pencil-square" />
        </a>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Clone: Clone this provider resource to a new resource owned by you"
          onClick={() => handleCloneButtonClicked(provider)}
          tabIndex={0}
        >
          <i className="bi bi-files" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Rename: Rename this provider resource"
          onClick={() => handleRenameButtonClicked(provider)}
          tabIndex={0}
        >
          <i className="bi bi-pencil" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Delete: Delete this provider resource"
          onClick={() => handleDeleteButtonClicked(provider)}
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

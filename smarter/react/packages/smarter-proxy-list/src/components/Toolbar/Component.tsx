/**
 * Toolbar React Component
 *
 * This component provides a toolbar for managing proxy resources, used in both ListView and CardView displays.
 * It offers actions for opening, editing, cloning, renaming, and deleting a proxy, with modal dialogs for confirmation and error handling.
 *
 * Features:
 * - Action buttons for: Open (chat), Edit (YAML manifest), Clone, Rename, and Delete proxy resources.
 * - Modal dialogs for clone, rename, delete, error, and confirmation workflows.
 * - Ensures only one modal is open at a time for clear user interaction.
 * - Handles API calls for clone, rename, and delete operations, with feedback on success or failure.
 * - Accessible with ARIA labels and keyboard navigation.
 *
 * Props:
 * - sessionContext (SessionContext): Contains authentication and API information for backend operations.
 * - proxy (Proxy): The proxy resource to manage.
 *
 * Usage:
 * <Toolbar sessionContext={sessionContext} proxy={proxy} />
 *
 * This component is intended to be embedded in each proxy row or card in ListView and CardView.
 */
import { useState } from "react";
import type { SessionContext } from "@smarter/common";
import { fetchDjangoUrl, Modal } from "@smarter/common";

import { loggerPrefix } from "@/lib/const";
import type { Proxy } from "@/lib/Types";

interface ToolbarProps {
  sessionContext: SessionContext;
  proxy: Proxy;
  onRequery: () => void;
}

export const Toolbar = ({ sessionContext, proxy, onRequery }: ToolbarProps) => {
  // this is a single way to control which and whether a modal is open.
  // it ensures that only one modal can be open at a time, and simplifies
  // the logic for opening and closing any of the four modals.
  // url: string, csrfToken: string, djangoSessionCookieName: string, csrfCookieName: string, cookieDomain: string
  const [modal, setModal] = useState<{
    type: null | "clone" | "rename" | "delete" | "confirmation" | "error";
    proxy: Proxy | null;
  }>({ type: null, proxy: null });
  const [errMessage, setErrMessage] = useState<string>("");
  const [successMessage, setSuccessMessage] = useState<string>("");

  const handleCloseModal = () => {
    setModal({ type: null, proxy: null });
  };
  const handleCloseModalWithRequery = () => {
    setModal({ type: null, proxy: null });
    onRequery();
  };

  const handleCloneButtonClicked = (proxy: Proxy) => setModal({ type: "clone", proxy });
  const handleRenameButtonClicked = (proxy: Proxy) => setModal({ type: "rename", proxy });
  const handleDeleteButtonClicked = (proxy: Proxy) => setModal({ type: "delete", proxy });

  const handleError = (proxy: Proxy) => {
    handleCloseModal();
    setModal({ type: "error", proxy });
  };

  const ModalClone = () => {
    const [inputValue, setInputValue] = useState("");
    return (
      <>
        <Modal
          show={modal.type === "clone"}
          title="Clone Proxy"
          onOk={() => handleCloneProxy(modal.proxy!, inputValue)}
          onCancel={handleCloseModal}
        >
          <p>
            Clone proxy <strong>{modal.proxy?.name}</strong> to a new resource owned by you.
          </p>
          <p>
            <em>Provide the new name for the cloned proxy.</em>
          </p>
          <input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Enter new proxy name"
          />
        </Modal>
      </>
    );
  };

  const ModalRename = () => {
    const [inputValue, setInputValue] = useState(modal.proxy?.name || "");
    return (
      <>
        <Modal
          show={modal.type === "rename"}
          title="Rename Proxy"
          onOk={() => handleRenameProxy(modal.proxy!, inputValue)}
          onCancel={handleCloseModal}
        >
          <p>
            Rename proxy <strong>{modal.proxy?.name}</strong>.
          </p>
          <p>
            <em>Provide the new name for the proxy.</em>
          </p>
          <input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Enter new proxy name"
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
          title="Delete Proxy"
          onOk={() => handleDeleteProxy(modal.proxy!)}
          onCancel={handleCloseModal}
        >
          <p>
            Are you sure you want to delete proxy <strong>{modal.proxy?.name}</strong>?
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
            An error occurred while performing the operation on proxy <strong>{modal.proxy?.name}</strong>.
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
            {successMessage} <strong>{modal.proxy?.name}</strong>.
          </p>
          <p>
            <em>Operation completed successfully.</em>
          </p>
        </Modal>
      </>
    );
  };

  const handleCloneProxy = async (proxy: Proxy, new_name: string) => {
    // see: smarter.apps.proxy.urls for API urls
    // path("api/clone/<int:proxy_id>/<str:new_name>/", ProxyListApiCloneView.as_view(), name=ProxyReverseNames.listview_api_clone),
    //
    // implement the clone logic here, e.g. call an API route to perform the clone operation.
    // return a success or failure result.

    const url = sessionContext.ApiUrl + "clone/" + proxy.id + "/" + new_name + "/";
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
              throw new Error(`Failed to clone proxy (${response.status}): ${errorMessage}`);
            })
            .catch(() => {
              throw new Error(`Failed to clone proxy (${response.status}): ${response.statusText}`);
            });
        }
        return response.json();
      })
      .then((data: Proxy) => {
        console.debug(loggerPrefix, "Successfully cloned proxy:", data);
        setModal({ type: "confirmation", proxy: data as Proxy });
        setSuccessMessage(`Successfully cloned proxy`);
      })
      .catch((error) => {
        console.error(loggerPrefix, "Error cloning proxy:", error);
        setErrMessage(error.message);
        handleError(proxy);
      });
    return true;
  };

  const handleRenameProxy = async (proxy: Proxy, newName: string) => {
    // implement the rename logic here, e.g. call an API route to perform the rename operation.
    // return a success or failure result.
    handleCloseModal();
    const url = sessionContext.ApiUrl + "rename/" + proxy.id + "/" + newName + "/";

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
              throw new Error(`Failed to rename proxy (${response.status}): ${errorMessage}`);
            })
            .catch(() => {
              throw new Error(`Failed to rename proxy (${response.status}): ${response.statusText}`);
            });
        }
        return response.json();
      })
      .then((data: Proxy) => {
        console.debug(loggerPrefix, "Successfully renamed proxy:", data);
        setModal({ type: "confirmation", proxy: data as Proxy });
        setSuccessMessage(`Successfully renamed proxy`);
      })
      .catch((error) => {
        console.error(loggerPrefix, "Error renaming proxy:", error);
        setErrMessage(error.message);
        handleError(proxy);
      });
    return true;
  };

  const handleDeleteProxy = async (proxy: Proxy) => {
    // implement the delete logic here, e.g. call an API route to perform the delete operation.
    // return a success or failure result.
    handleCloseModal();
    const url = sessionContext.ApiUrl + "delete/" + proxy.id + "/";
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
              throw new Error(`Failed to delete proxy (${response.status}): ${errorMessage}`);
            })
            .catch(() => {
              throw new Error(`Failed to delete proxy (${response.status}): ${response.statusText}`);
            });
        }
        return response.json();
      })
      .then(() => {
        console.debug(loggerPrefix, "Successfully deleted proxy:", proxy);
        setModal({ type: "confirmation", proxy });
        setSuccessMessage(`Successfully deleted proxy`);
      })
      .catch((error) => {
        console.error(loggerPrefix, "Error deleting proxy:", error);
        setErrMessage(error.message);
        handleError(proxy);
      });
    return true;
  };

  return (
    <>
      <div className="toolbar btn-group pe-2" role="group" aria-label="Actions">
        <a
          href={proxy.manifestUrl}
          className="btn btn-icon btn-sm border"
          title="Chat: Open the proxy workbench"
          tabIndex={0}
        >
          <i className="bi bi-chat-dots" />
        </a>
        <a
          href={proxy.manifestUrl}
          className="btn btn-icon btn-sm border"
          title="Edit: Open the YAML manifest that defines this proxy resource"
          tabIndex={0}
        >
          <i className="bi bi-pencil-square" />
        </a>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Clone: Clone this proxy resource to a new resource owned by you"
          onClick={() => handleCloneButtonClicked(proxy)}
          tabIndex={0}
        >
          <i className="bi bi-files" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Rename: Rename this proxy resource"
          onClick={() => handleRenameButtonClicked(proxy)}
          tabIndex={0}
        >
          <i className="bi bi-pencil" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Delete: Delete this proxy resource"
          onClick={() => handleDeleteButtonClicked(proxy)}
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

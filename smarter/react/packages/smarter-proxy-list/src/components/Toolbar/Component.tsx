/**
 * Toolbar React Component
 *
 * This component provides a toolbar for managing proxy resources, used in both ListView and CardView displays.
 * It offers actions for opening, editing, cloning, renaming, and deleting a proxy, with modal dialogs for confirmation and error handling.
 *
 * Features:
 * - Action buttons for: Copy URL (the base URL for the provider's SDK), Edit (YAML manifest), Clone, Rename,
 *   and Delete proxy resources.
 * - Modal dialogs for clone, rename, delete, error, and confirmation workflows.
 * - Ensures only one modal is open at a time for clear user interaction.
 * - Handles API calls for clone, rename, and delete operations, with feedback on success or failure,
 *   including the server's error message.
 * - Accessible with ARIA labels and keyboard navigation.
 *
 * The modals are defined outside of Toolbar, so that React does not recreate, and reset, them
 * each time Toolbar renders.
 *
 * Props:
 * - sessionContext (SessionContext): Contains authentication and API information for backend operations.
 * - proxy (Proxy): The proxy resource to manage.
 *
 * Usage:
 * <Toolbar sessionContext={sessionContext} proxy={proxy} onRequery={onRequery} />
 *
 * This component is intended to be embedded in each proxy row or card in ListView and CardView.
 */
import { useState } from "react";
import type { SessionContext } from "@smarter/common";
import { actionUrl, fetchDjangoUrl, Modal } from "@smarter/common";

import { loggerPrefix } from "@/lib/const";
import { proxyUrl } from "@/lib/format";
import type { Proxy } from "@/lib/Types";
import "./styles.css";

type ModalType = null | "clone" | "rename" | "delete" | "confirmation" | "error";

interface NameModalProps {
  proxy: Proxy | null;
  onOk: (newName: string) => void;
  onCancel: () => void;
}

/** Asks for the name of the clone. It is mounted only while open, so it starts empty. */
const ModalClone = ({ proxy, onOk, onCancel }: NameModalProps) => {
  const [inputValue, setInputValue] = useState("");
  return (
    <Modal show title="Clone Proxy" onOk={() => onOk(inputValue)} onCancel={onCancel}>
      <p>
        Clone proxy <strong>{proxy?.name}</strong> to a new resource owned by you.
      </p>
      <p>
        <em>Provide the new name for the cloned proxy.</em>
      </p>
      <input value={inputValue} onChange={(e) => setInputValue(e.target.value)} placeholder="Enter new proxy name" />
    </Modal>
  );
};

/** Asks for the new name. It is mounted only while open, so it starts with the current name. */
const ModalRename = ({ proxy, onOk, onCancel }: NameModalProps) => {
  const [inputValue, setInputValue] = useState(proxy?.name || "");
  return (
    <Modal show title="Rename Proxy" onOk={() => onOk(inputValue)} onCancel={onCancel}>
      <p>
        Rename proxy <strong>{proxy?.name}</strong>.
      </p>
      <p>
        <em>Provide the new name for the proxy.</em>
      </p>
      <input value={inputValue} onChange={(e) => setInputValue(e.target.value)} placeholder="Enter new proxy name" />
    </Modal>
  );
};

/** Confirms the deletion. */
const ModalDelete = ({
  show,
  proxy,
  onOk,
  onCancel,
}: {
  show: boolean;
  proxy: Proxy | null;
  onOk: () => void;
  onCancel: () => void;
}) => (
  <Modal show={show} title="Delete Proxy" onOk={onOk} onCancel={onCancel}>
    <p>
      Are you sure you want to delete proxy <strong>{proxy?.name}</strong>?
    </p>
    <p>
      <em>Data is not recoverable.</em>
    </p>
  </Modal>
);

/** Shows the error message. */
const ModalError = ({
  show,
  proxy,
  message,
  onClose,
}: {
  show: boolean;
  proxy: Proxy | null;
  message: string;
  onClose: () => void;
}) => (
  <Modal show={show} title="❌ Error" onClose={onClose}>
    <p>
      An error occurred while performing the operation on proxy <strong>{proxy?.name}</strong>.
    </p>
    <p>{message ? <span className="text-danger">{message}</span> : <em>An unknown error occurred.</em>}</p>
  </Modal>
);

/** Confirms that the operation succeeded. */
const ModalConfirmation = ({
  show,
  proxy,
  message,
  onClose,
}: {
  show: boolean;
  proxy: Proxy | null;
  message: string;
  onClose: () => void;
}) => (
  <Modal show={show} title="✅ Success" onClose={onClose}>
    <p>
      {message} <strong>{proxy?.name}</strong>.
    </p>
    <p>
      <em>Operation completed successfully.</em>
    </p>
  </Modal>
);

interface ToolbarProps {
  sessionContext: SessionContext;
  proxy: Proxy;
  onRequery: () => void;
}

export const Toolbar = ({ sessionContext, proxy, onRequery }: ToolbarProps) => {
  // this is a single way to control which and whether a modal is open.
  // it ensures that only one modal can be open at a time.
  const [modal, setModal] = useState<{ type: ModalType; proxy: Proxy | null }>({ type: null, proxy: null });
  const [errMessage, setErrMessage] = useState<string>("");
  const [successMessage, setSuccessMessage] = useState<string>("");
  const [copied, setCopied] = useState<boolean>(false);

  const handleCloseModal = () => {
    setModal({ type: null, proxy: null });
  };
  const handleCloseModalWithRequery = () => {
    setModal({ type: null, proxy: null });
    onRequery();
  };

  /**
   * POST to one of the list API's actions, e.g. clone/12/new_name/, and show the result: the
   * confirmation modal on success, else the error modal with the server's error message.
   * See actionUrl() in @smarter/common for how the action's URL is built.
   */
  const runAction = (target: Proxy, path: string, verb: "clone" | "rename" | "delete") => {
    handleCloseModal();
    fetchDjangoUrl(sessionContext, actionUrl(sessionContext, path), JSON.stringify({}))
      .then(async (response) => {
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(`Failed to ${verb} proxy (${response.status}): ${data.error || response.statusText}`);
        }
        return data;
      })
      .then((data) => {
        console.debug(loggerPrefix, `Successfully ${verb}d proxy:`, data);
        setSuccessMessage(`Successfully ${verb}d proxy`);
        // clone and rename return the resulting proxy; delete returns a message.
        setModal({ type: "confirmation", proxy: data && data.id ? (data as Proxy) : target });
      })
      .catch((error) => {
        console.error(loggerPrefix, `Error trying to ${verb} proxy:`, error);
        setErrMessage(error.message);
        setModal({ type: "error", proxy: target });
      });
  };

  /** Copy the Proxy's URL, which callers use as the base URL of the provider's SDK, to the clipboard. */
  const copyUrl = () => {
    navigator.clipboard
      .writeText(proxyUrl(proxy))
      .then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      })
      .catch((error) => {
        console.error(loggerPrefix, "Error copying the proxy URL:", error);
        setErrMessage(`Could not copy the URL to the clipboard: ${proxyUrl(proxy)}`);
        setModal({ type: "error", proxy });
      });
  };

  return (
    <>
      <div className="toolbar btn-group pe-2" role="group" aria-label="Actions">
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title={
            proxy.url
              ? `Copy URL: ${proxyUrl(proxy)}. Use it as the base URL of the provider's SDK, with a Smarter API key.`
              : "The proxy endpoints are disabled. Set SMARTER_ENABLE_PROXY=true."
          }
          onClick={copyUrl}
          disabled={!proxy.url}
          tabIndex={0}
        >
          <i className={copied ? "bi bi-clipboard-check md-green" : "bi bi-clipboard md-teal"} />
        </button>
        <a
          href={proxy.manifestUrl}
          className="btn btn-icon btn-sm border"
          title="Edit: Open the YAML manifest that defines this proxy resource"
          tabIndex={0}
        >
          <i className="bi bi-pencil-square md-blue" />
        </a>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Clone: Clone this proxy resource to a new resource owned by you"
          onClick={() => setModal({ type: "clone", proxy })}
          tabIndex={0}
        >
          <i className="bi bi-files md-green" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Rename: Rename this proxy resource"
          onClick={() => setModal({ type: "rename", proxy })}
          tabIndex={0}
        >
          <i className="bi bi-pencil md-blue" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title={
            proxy.canDelete === false
              ? "Delete: You can't delete this proxy, because other resources depend on it, or you don't have permission to delete it"
              : "Delete: Delete this proxy resource"
          }
          onClick={() => setModal({ type: "delete", proxy })}
          disabled={proxy.canDelete === false}
          tabIndex={0}
        >
          <i className="bi bi-trash md-red" />
        </button>
      </div>

      <div>
        {modal.type === "clone" && (
          <ModalClone
            proxy={modal.proxy}
            onOk={(newName) => runAction(modal.proxy!, `clone/${modal.proxy!.id}/${newName}/`, "clone")}
            onCancel={handleCloseModal}
          />
        )}
        {modal.type === "rename" && (
          <ModalRename
            proxy={modal.proxy}
            onOk={(newName) => runAction(modal.proxy!, `rename/${modal.proxy!.id}/${newName}/`, "rename")}
            onCancel={handleCloseModal}
          />
        )}
        <ModalDelete
          show={modal.type === "delete"}
          proxy={modal.proxy}
          onOk={() => runAction(modal.proxy!, `delete/${modal.proxy!.id}/`, "delete")}
          onCancel={handleCloseModal}
        />
        <ModalError show={modal.type === "error"} proxy={modal.proxy} message={errMessage} onClose={handleCloseModal} />
        <ModalConfirmation
          show={modal.type === "confirmation"}
          proxy={modal.proxy}
          message={successMessage}
          onClose={handleCloseModalWithRequery}
        />
      </div>
    </>
  );
};

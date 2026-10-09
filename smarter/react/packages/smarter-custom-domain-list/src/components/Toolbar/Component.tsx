/**
 * Toolbar React Component
 *
 * This component provides a toolbar for managing custom domain resources, used in both ListView and CardView displays.
 * It offers actions for opening, editing, cloning, renaming, and deleting a custom domain, with modal dialogs for confirmation and error handling.
 *
 * Features:
 * - Action buttons for: Open (the LLMClient that uses the domain), Edit (YAML manifest), Visit (the
 *   LLMClient's url on the domain), Clone, Rename, and Delete.
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
 * - customDomain (CustomDomain): The custom domain to manage.
 *
 * Usage:
 * <Toolbar sessionContext={sessionContext} customDomain={customDomain} onRequery={onRequery} />
 *
 * This component is intended to be embedded in each custom domain row or card in ListView and CardView.
 */
import { useState } from "react";
import type { SessionContext } from "@smarter/common";
import { actionUrl, fetchDjangoUrl, Modal } from "@smarter/common";

import { loggerPrefix } from "@/lib/const";
import type { CustomDomain } from "@/lib/Types";
import "@/components/Toolbar/styles.css";

type ModalType = null | "clone" | "rename" | "delete" | "confirmation" | "error";

interface NameModalProps {
  customDomain: CustomDomain | null;
  onOk: (newName: string) => void;
  onCancel: () => void;
}

/** Asks for the name of the clone. It is mounted only while open, so it starts empty. */
const ModalClone = ({ customDomain, onOk, onCancel }: NameModalProps) => {
  const [inputValue, setInputValue] = useState("");
  return (
    <Modal show title="Clone Custom Domain" onOk={() => onOk(inputValue)} onCancel={onCancel}>
      <p>
        Clone custom domain <strong>{customDomain?.name}</strong> to a new resource owned by you.
      </p>
      <p>
        <em>Provide the new name for the cloned custom domain.</em>
      </p>
      <input
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        placeholder="Enter new custom domain name"
      />
    </Modal>
  );
};

/** Asks for the new name. It is mounted only while open, so it starts with the current name. */
const ModalRename = ({ customDomain, onOk, onCancel }: NameModalProps) => {
  const [inputValue, setInputValue] = useState(customDomain?.name || "");
  return (
    <Modal show title="Rename Custom Domain" onOk={() => onOk(inputValue)} onCancel={onCancel}>
      <p>
        Rename custom domain <strong>{customDomain?.name}</strong>.
      </p>
      <p>
        <em>Provide the new name for the custom domain.</em>
      </p>
      <input
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        placeholder="Enter new custom domain name"
      />
    </Modal>
  );
};

/** Confirms the deletion. */
const ModalDelete = ({
  show,
  customDomain,
  onOk,
  onCancel,
}: {
  show: boolean;
  customDomain: CustomDomain | null;
  onOk: () => void;
  onCancel: () => void;
}) => (
  <Modal show={show} title="Delete Custom Domain" onOk={onOk} onCancel={onCancel}>
    <p>
      Are you sure you want to delete custom domain <strong>{customDomain?.name}</strong>?
    </p>
    <p>
      <em>Data is not recoverable.</em>
    </p>
  </Modal>
);

/** Shows the error message. */
const ModalError = ({
  show,
  customDomain,
  message,
  onClose,
}: {
  show: boolean;
  customDomain: CustomDomain | null;
  message: string;
  onClose: () => void;
}) => (
  <Modal show={show} title="❌ Error" onClose={onClose}>
    <p>
      An error occurred while performing the operation on custom domain <strong>{customDomain?.name}</strong>.
    </p>
    <p>{message ? <span className="text-danger">{message}</span> : <em>An unknown error occurred.</em>}</p>
  </Modal>
);

/** Confirms that the operation succeeded. */
const ModalConfirmation = ({
  show,
  customDomain,
  message,
  onClose,
}: {
  show: boolean;
  customDomain: CustomDomain | null;
  message: string;
  onClose: () => void;
}) => (
  <Modal show={show} title="✅ Success" onClose={onClose}>
    <p>
      {message} <strong>{customDomain?.name}</strong>.
    </p>
    <p>
      <em>Operation completed successfully.</em>
    </p>
  </Modal>
);

/** A link to a page, rendered as a disabled button when it has nowhere to go. */
const ToolbarLink = ({
  href,
  title,
  disabledTitle,
  icon,
  external = false,
}: {
  href: string | null | undefined;
  title: string;
  disabledTitle: string;
  icon: string;
  external?: boolean;
}) =>
  href ? (
    <a
      href={href}
      className="btn btn-icon btn-sm border"
      title={title}
      tabIndex={0}
      {...(external ? { target: "_blank", rel: "noopener noreferrer" } : {})}
    >
      <i className={icon} />
    </a>
  ) : (
    <button type="button" className="btn btn-icon btn-sm border" title={disabledTitle} disabled tabIndex={0}>
      <i className={icon} />
    </button>
  );

interface ToolbarProps {
  sessionContext: SessionContext;
  customDomain: CustomDomain;
  onRequery: () => void;
}

export const Toolbar = ({ sessionContext, customDomain, onRequery }: ToolbarProps) => {
  // this is a single way to control which and whether a modal is open.
  // it ensures that only one modal can be open at a time.
  const [modal, setModal] = useState<{ type: ModalType; customDomain: CustomDomain | null }>({
    type: null,
    customDomain: null,
  });
  const [errMessage, setErrMessage] = useState<string>("");
  const [successMessage, setSuccessMessage] = useState<string>("");

  const handleCloseModal = () => {
    setModal({ type: null, customDomain: null });
  };
  const handleCloseModalWithRequery = () => {
    setModal({ type: null, customDomain: null });
    onRequery();
  };

  /**
   * POST to one of the list API's actions, e.g. clone/12/new_name/, and show the result: the
   * confirmation modal on success, else the error modal with the server's error message.
   * See actionUrl() in @smarter/common for how the action's URL is built.
   */
  const runAction = (target: CustomDomain, path: string, verb: "clone" | "rename" | "delete") => {
    handleCloseModal();
    fetchDjangoUrl(sessionContext, actionUrl(sessionContext, path), JSON.stringify({}))
      .then(async (response) => {
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(`Failed to ${verb} custom domain (${response.status}): ${data.error || response.statusText}`);
        }
        return data;
      })
      .then((data) => {
        console.debug(loggerPrefix, `Successfully ${verb}d custom domain:`, data);
        setSuccessMessage(`Successfully ${verb}d custom domain`);
        // clone and rename return the resulting customDomain; delete returns a message.
        setModal({ type: "confirmation", customDomain: data && data.id ? (data as CustomDomain) : target });
      })
      .catch((error) => {
        console.error(loggerPrefix, `Error trying to ${verb} custom domain:`, error);
        setErrMessage(error.message);
        setModal({ type: "error", customDomain: target });
      });
  };

  return (
    <>
      <div className="toolbar btn-group pe-2" role="group" aria-label="Actions">
        <ToolbarLink
          href={customDomain.llmclient?.sandboxUrl}
          title={`Open: Open LLMClient ${customDomain.llmclient?.name} in the workbench`}
          disabledTitle="Open: No LLMClient uses this custom domain"
          icon="bi bi-chat-dots md-teal"
        />
        <a
          href={customDomain.manifestUrl}
          className="btn btn-icon btn-sm border"
          title="Edit: Open the YAML manifest that defines this custom domain"
          tabIndex={0}
        >
          <i className="bi bi-pencil-square md-blue" />
        </a>
        <ToolbarLink
          href={customDomain.verificationStatus === "Verified" ? customDomain.llmclient?.url : null}
          title={`Visit: ${customDomain.llmclient?.url}`}
          disabledTitle={
            customDomain.llmclient
              ? "Visit: The custom domain is not verified yet"
              : "Visit: No LLMClient uses this custom domain"
          }
          icon="bi bi-box-arrow-up-right md-green"
          external
        />
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Clone: Clone this custom domain to a new resource owned by you"
          onClick={() => setModal({ type: "clone", customDomain })}
          tabIndex={0}
        >
          <i className="bi bi-files md-green" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title="Rename: Rename this custom domain"
          onClick={() => setModal({ type: "rename", customDomain })}
          tabIndex={0}
        >
          <i className="bi bi-pencil md-blue" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title={
            customDomain.canDelete === false
              ? "Delete: You can't delete this custom domain, because an LLMClient uses it, or you don't have permission to delete it"
              : "Delete: Delete this custom domain"
          }
          onClick={() => setModal({ type: "delete", customDomain })}
          disabled={customDomain.canDelete === false}
          tabIndex={0}
        >
          <i className="bi bi-trash md-red" />
        </button>
      </div>

      <div>
        {modal.type === "clone" && (
          <ModalClone
            customDomain={modal.customDomain}
            onOk={(newName) => runAction(modal.customDomain!, `clone/${modal.customDomain!.id}/${newName}/`, "clone")}
            onCancel={handleCloseModal}
          />
        )}
        {modal.type === "rename" && (
          <ModalRename
            customDomain={modal.customDomain}
            onOk={(newName) => runAction(modal.customDomain!, `rename/${modal.customDomain!.id}/${newName}/`, "rename")}
            onCancel={handleCloseModal}
          />
        )}
        <ModalDelete
          show={modal.type === "delete"}
          customDomain={modal.customDomain}
          onOk={() => runAction(modal.customDomain!, `delete/${modal.customDomain!.id}/`, "delete")}
          onCancel={handleCloseModal}
        />
        <ModalError
          show={modal.type === "error"}
          customDomain={modal.customDomain}
          message={errMessage}
          onClose={handleCloseModal}
        />
        <ModalConfirmation
          show={modal.type === "confirmation"}
          customDomain={modal.customDomain}
          message={successMessage}
          onClose={handleCloseModalWithRequery}
        />
      </div>
    </>
  );
};

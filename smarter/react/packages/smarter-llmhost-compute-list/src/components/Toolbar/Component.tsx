/**
 * Toolbar React Component
 *
 * This component provides a toolbar for managing LLMHostCompute resources, used in ListView and in the DetailView of a resource's detail.
 * It offers actions for viewing the manifest, cloning, renaming, and deleting an LLMHostCompute, with modal dialogs
 * for confirmation and error handling.
 *
 * Features:
 * - Action buttons for: Edit (YAML manifest), Clone, Rename, and Delete.
 * - Modal dialogs for clone, rename, delete, error, and confirmation workflows.
 * - Ensures only one modal is open at a time for clear user interaction.
 * - Handles API calls for clone, rename, and delete operations, with feedback on success or failure.
 *   The server refuses to rename an LLMHostCompute while its node group exists, and to delete one
 *   while LLMHosts use it; its error message is shown.
 * - Accessible with ARIA labels and keyboard navigation.
 *
 * Props:
 * - sessionContext (SessionContext): Contains authentication and API information for backend operations.
 * - compute (LLMHostCompute): The LLMHostCompute resource to manage.
 *
 * Usage:
 * <Toolbar sessionContext={sessionContext} compute={compute} onRequery={onRequery} />
 */
import { useState } from "react";
import type { SessionContext } from "@smarter/common";
import { actionUrl, fetchDjangoUrl, gettext, interpolate, interpolateNodes, Modal } from "@smarter/common";

import { loggerPrefix } from "@/lib/const";
import type { LLMHostCompute } from "@/lib/Types";
import "@/components/Toolbar/styles.css";

/**
 * The messages that report the result of an action. Each is a whole sentence, so that it can be
 * translated.
 */
const actionMessages = (verb: string) => {
  switch (verb) {
    case "clone":
      return {
        failed: gettext("Failed to clone LLMHostCompute (%(status)s): %(error)s"),
        succeeded: gettext("Successfully cloned LLMHostCompute"),
      };
    case "rename":
      return {
        failed: gettext("Failed to rename LLMHostCompute (%(status)s): %(error)s"),
        succeeded: gettext("Successfully renamed LLMHostCompute"),
      };
    default:
      return {
        failed: gettext("Failed to delete LLMHostCompute (%(status)s): %(error)s"),
        succeeded: gettext("Successfully deleted LLMHostCompute"),
      };
  }
};

interface ToolbarProps {
  sessionContext: SessionContext;
  compute: LLMHostCompute;
  onRequery: () => void;
}

type ModalType = null | "clone" | "rename" | "delete" | "confirmation" | "error";

interface NameModalProps {
  show: boolean;
  compute: LLMHostCompute | null;
  onOk: (newName: string) => void;
  onCancel: () => void;
}

/** Asks for the name of the clone. */
const ModalClone = ({ show, compute, onOk, onCancel }: NameModalProps) => {
  const [inputValue, setInputValue] = useState("");
  return (
    <Modal show={show} title={gettext("Clone LLMHostCompute")} onOk={() => onOk(inputValue)} onCancel={onCancel}>
      <p>
        {interpolateNodes(gettext("Clone %(name)s to a new LLMHostCompute owned by you."), {
          name: <strong>{compute?.name}</strong>,
        })}
      </p>
      <p>
        <em>
          {gettext(
            "The clone has the same kind of node, and its own node group, which Smarter creates when an LLMHost first needs one of its nodes.",
          )}
        </em>
      </p>
      <input
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        placeholder={gettext("Enter new name")}
      />
    </Modal>
  );
};

/** Asks for the new name. */
const ModalRename = ({ show, compute, onOk, onCancel }: NameModalProps) => {
  const [inputValue, setInputValue] = useState(compute?.name || "");
  return (
    <Modal show={show} title={gettext("Rename LLMHostCompute")} onOk={() => onOk(inputValue)} onCancel={onCancel}>
      <p>{interpolateNodes(gettext("Rename %(name)s."), { name: <strong>{compute?.name}</strong> })}</p>
      <p>
        <em>{gettext("Not possible while its node group exists, or LLMHosts use it.")}</em>
      </p>
      <input
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        placeholder={gettext("Enter new name")}
      />
    </Modal>
  );
};

/** Confirms the deletion. */
const ModalDelete = ({
  show,
  compute,
  onOk,
  onCancel,
}: {
  show: boolean;
  compute: LLMHostCompute | null;
  onOk: () => void;
  onCancel: () => void;
}) => (
  <Modal show={show} title={gettext("Delete LLMHostCompute")} onOk={onOk} onCancel={onCancel}>
    <p>
      {interpolateNodes(gettext("Are you sure you want to delete %(name)s?"), {
        name: <strong>{compute?.name}</strong>,
      })}
    </p>
    <p>
      <em>{gettext("Its node group, and any nodes in it, are deleted too. Not possible while LLMHosts use it.")}</em>
    </p>
  </Modal>
);

/** Shows the server's error message. */
const ModalError = ({
  show,
  compute,
  message,
  onClose,
}: {
  show: boolean;
  compute: LLMHostCompute | null;
  message: string;
  onClose: () => void;
}) => (
  <Modal show={show} title={gettext("❌ Error")} onClose={onClose}>
    <p>
      {interpolateNodes(gettext("An error occurred while performing the operation on %(name)s."), {
        name: <strong>{compute?.name}</strong>,
      })}
    </p>
    <p>{message ? <span className="text-danger">{message}</span> : <em>{gettext("An unknown error occurred.")}</em>}</p>
  </Modal>
);

/** Confirms that the operation succeeded. */
const ModalConfirmation = ({
  show,
  compute,
  message,
  onClose,
}: {
  show: boolean;
  compute: LLMHostCompute | null;
  message: string;
  onClose: () => void;
}) => (
  <Modal show={show} title={gettext("✅ Success")} onClose={onClose}>
    <p>
      {message} <strong>{compute?.name}</strong>.
    </p>
    <p>
      <em>{gettext("Operation completed successfully.")}</em>
    </p>
  </Modal>
);

export const Toolbar = ({ sessionContext, compute, onRequery }: ToolbarProps) => {
  // this is a single way to control which and whether a modal is open.
  // it ensures that only one modal can be open at a time.
  const [modal, setModal] = useState<{ type: ModalType; compute: LLMHostCompute | null }>({
    type: null,
    compute: null,
  });
  const [errMessage, setErrMessage] = useState<string>("");
  const [successMessage, setSuccessMessage] = useState<string>("");

  const handleCloseModal = () => {
    setModal({ type: null, compute: null });
  };
  const handleCloseModalWithRequery = () => {
    setModal({ type: null, compute: null });
    onRequery();
  };

  const handleError = (compute: LLMHostCompute) => {
    handleCloseModal();
    setModal({ type: "error", compute });
  };

  /**
   * POST to a list API action, and show the result: the confirmation modal on success, else the
   * error modal with the server's error message.
   */
  const runAction = (compute: LLMHostCompute, path: string, verb: string) => {
    handleCloseModal();
    fetchDjangoUrl(sessionContext, actionUrl(sessionContext, path), JSON.stringify({}))
      .then(async (response) => {
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(
            data.error ||
              interpolate(actionMessages(verb).failed, { status: response.status, error: response.statusText }),
          );
        }
        return data;
      })
      .then((data) => {
        console.debug(loggerPrefix, `Successfully ${verb}d LLMHostCompute:`, data);
        setSuccessMessage(actionMessages(verb).succeeded);
        setModal({ type: "confirmation", compute: data && data.id ? (data as LLMHostCompute) : compute });
      })
      .catch((error) => {
        console.error(loggerPrefix, `Error ${verb.replace(/e$/, "")}ing LLMHostCompute:`, error);
        setErrMessage(error.message);
        handleError(compute);
      });
    return true;
  };

  return (
    <>
      <div className="toolbar btn-group pe-2" role="group" aria-label={gettext("Actions")}>
        <a
          href={compute.manifestUrl}
          className="btn btn-icon btn-sm border"
          title={gettext(
            "Manifest: Open the YAML manifest that defines this LLMHostCompute, with its node group's status",
          )}
          tabIndex={0}
        >
          <i className="bi bi-pencil-square md-blue" />
        </a>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title={gettext("Clone: Clone this LLMHostCompute to a new resource owned by you")}
          onClick={() => setModal({ type: "clone", compute })}
          tabIndex={0}
        >
          <i className="bi bi-files md-green" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title={gettext("Rename: Rename this LLMHostCompute")}
          onClick={() => setModal({ type: "rename", compute })}
          tabIndex={0}
        >
          <i className="bi bi-pencil md-blue" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title={
            compute.canDelete === false
              ? gettext(
                  "Delete: You can't delete this LLMHostCompute, because other resources depend on it, or you don't have permission to delete it",
                )
              : gettext("Delete: Delete this LLMHostCompute and its node group")
          }
          onClick={() => setModal({ type: "delete", compute })}
          disabled={compute.canDelete === false}
          tabIndex={0}
        >
          <i className="bi bi-trash md-red" />
        </button>
      </div>

      <div>
        {modal.type === "clone" && (
          <ModalClone
            show
            compute={modal.compute}
            onOk={(newName) => runAction(modal.compute!, `clone/${modal.compute!.id}/${newName}/`, "clone")}
            onCancel={handleCloseModal}
          />
        )}
        {modal.type === "rename" && (
          <ModalRename
            show
            compute={modal.compute}
            onOk={(newName) => runAction(modal.compute!, `rename/${modal.compute!.id}/${newName}/`, "rename")}
            onCancel={handleCloseModal}
          />
        )}
        <ModalDelete
          show={modal.type === "delete"}
          compute={modal.compute}
          onOk={() => runAction(modal.compute!, `delete/${modal.compute!.id}/`, "delete")}
          onCancel={handleCloseModal}
        />
        <ModalError
          show={modal.type === "error"}
          compute={modal.compute}
          message={errMessage}
          onClose={handleCloseModal}
        />
        <ModalConfirmation
          show={modal.type === "confirmation"}
          compute={modal.compute}
          message={successMessage}
          onClose={handleCloseModalWithRequery}
        />
      </div>
    </>
  );
};

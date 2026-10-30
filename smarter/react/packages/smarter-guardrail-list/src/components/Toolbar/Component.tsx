/**
 * Toolbar React Component
 *
 * This component provides a toolbar for managing guardrail resources, used in the ListView's rows and in the DetailView of a guardrail's detail.
 * It offers actions for opening, editing, cloning, renaming, and deleting a guardrail, with modal dialogs for confirmation and error handling.
 *
 * Features:
 * - Action buttons for: Open (chat), Edit (YAML manifest), Clone, Rename, and Delete guardrail resources.
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
 * - guardrail (Guardrail): The guardrail resource to manage.
 *
 * Usage:
 * <Toolbar sessionContext={sessionContext} guardrail={guardrail} onRequery={onRequery} />
 *
 * This component is intended to be embedded in each guardrail row of the ListView, and in the DetailView.
 */
import { useState } from "react";
import type { SessionContext } from "@smarter/common";
import { actionUrl, fetchDjangoUrl, gettext, interpolate, interpolateNodes, Modal } from "@smarter/common";

import { loggerPrefix } from "@/lib/const";
import type { Guardrail } from "@/lib/Types";
import "@/components/Toolbar/styles.css";

type ModalType = null | "clone" | "rename" | "delete" | "confirmation" | "error";

interface NameModalProps {
  guardrail: Guardrail | null;
  onOk: (newName: string) => void;
  onCancel: () => void;
}

/** Asks for the name of the clone. It is mounted only while open, so it starts empty. */
const ModalClone = ({ guardrail, onOk, onCancel }: NameModalProps) => {
  const [inputValue, setInputValue] = useState("");
  return (
    <Modal show title={gettext("Clone Guardrail")} onOk={() => onOk(inputValue)} onCancel={onCancel}>
      <p>
        {interpolateNodes(gettext("Clone guardrail %(name)s to a new resource owned by you."), {
          name: <strong>{guardrail?.name}</strong>,
        })}
      </p>
      <p>
        <em>{gettext("Provide the new name for the cloned guardrail.")}</em>
      </p>
      <input
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        placeholder={gettext("Enter new guardrail name")}
      />
    </Modal>
  );
};

/** Asks for the new name. It is mounted only while open, so it starts with the current name. */
const ModalRename = ({ guardrail, onOk, onCancel }: NameModalProps) => {
  const [inputValue, setInputValue] = useState(guardrail?.name || "");
  return (
    <Modal show title={gettext("Rename Guardrail")} onOk={() => onOk(inputValue)} onCancel={onCancel}>
      <p>{interpolateNodes(gettext("Rename guardrail %(name)s."), { name: <strong>{guardrail?.name}</strong> })}</p>
      <p>
        <em>{gettext("Provide the new name for the guardrail.")}</em>
      </p>
      <input
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        placeholder={gettext("Enter new guardrail name")}
      />
    </Modal>
  );
};

/** Confirms the deletion. */
const ModalDelete = ({
  show,
  guardrail,
  onOk,
  onCancel,
}: {
  show: boolean;
  guardrail: Guardrail | null;
  onOk: () => void;
  onCancel: () => void;
}) => (
  <Modal show={show} title={gettext("Delete Guardrail")} onOk={onOk} onCancel={onCancel}>
    <p>
      {interpolateNodes(gettext("Are you sure you want to delete guardrail %(name)s?"), {
        name: <strong>{guardrail?.name}</strong>,
      })}
    </p>
    <p>
      <em>{gettext("Data is not recoverable.")}</em>
    </p>
  </Modal>
);

/** Shows the error message. */
const ModalError = ({
  show,
  guardrail,
  message,
  onClose,
}: {
  show: boolean;
  guardrail: Guardrail | null;
  message: string;
  onClose: () => void;
}) => (
  <Modal show={show} title={gettext("❌ Error")} onClose={onClose}>
    <p>
      {interpolateNodes(gettext("An error occurred while performing the operation on guardrail %(name)s."), {
        name: <strong>{guardrail?.name}</strong>,
      })}
    </p>
    <p>{message ? <span className="text-danger">{message}</span> : <em>{gettext("An unknown error occurred.")}</em>}</p>
  </Modal>
);

/** Confirms that the operation succeeded. */
const ModalConfirmation = ({
  show,
  guardrail,
  message,
  onClose,
}: {
  show: boolean;
  guardrail: Guardrail | null;
  message: string;
  onClose: () => void;
}) => (
  <Modal show={show} title={gettext("✅ Success")} onClose={onClose}>
    <p>
      {message} <strong>{guardrail?.name}</strong>.
    </p>
    <p>
      <em>{gettext("Operation completed successfully.")}</em>
    </p>
  </Modal>
);

/**
 * The messages that report the result of an action. Each is a whole sentence, so that it can be
 * translated.
 */
const actionMessages = (verb: string) => {
  switch (verb) {
    case "clone":
      return {
        failed: gettext("Failed to clone guardrail (%(status)s): %(error)s"),
        succeeded: gettext("Successfully cloned guardrail"),
      };
    case "rename":
      return {
        failed: gettext("Failed to rename guardrail (%(status)s): %(error)s"),
        succeeded: gettext("Successfully renamed guardrail"),
      };
    default:
      return {
        failed: gettext("Failed to delete guardrail (%(status)s): %(error)s"),
        succeeded: gettext("Successfully deleted guardrail"),
      };
  }
};

interface ToolbarProps {
  sessionContext: SessionContext;
  guardrail: Guardrail;
  onRequery: () => void;
}

export const Toolbar = ({ sessionContext, guardrail, onRequery }: ToolbarProps) => {
  // this is a single way to control which and whether a modal is open.
  // it ensures that only one modal can be open at a time.
  const [modal, setModal] = useState<{ type: ModalType; guardrail: Guardrail | null }>({ type: null, guardrail: null });
  const [errMessage, setErrMessage] = useState<string>("");
  const [successMessage, setSuccessMessage] = useState<string>("");

  const handleCloseModal = () => {
    setModal({ type: null, guardrail: null });
  };
  const handleCloseModalWithRequery = () => {
    setModal({ type: null, guardrail: null });
    onRequery();
  };

  /**
   * POST to one of the list API's actions, e.g. clone/12/new_name/, and show the result: the
   * confirmation modal on success, else the error modal with the server's error message.
   * See actionUrl() in @smarter/common for how the action's URL is built.
   */
  const runAction = (target: Guardrail, path: string, verb: "clone" | "rename" | "delete") => {
    handleCloseModal();
    fetchDjangoUrl(sessionContext, actionUrl(sessionContext, path), JSON.stringify({}))
      .then(async (response) => {
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(
            interpolate(actionMessages(verb).failed, {
              status: response.status,
              error: data.error || response.statusText,
            }),
          );
        }
        return data;
      })
      .then((data) => {
        console.debug(loggerPrefix, `Successfully ${verb}d guardrail:`, data);
        setSuccessMessage(actionMessages(verb).succeeded);
        // clone and rename return the resulting guardrail; delete returns a message.
        setModal({ type: "confirmation", guardrail: data && data.id ? (data as Guardrail) : target });
      })
      .catch((error) => {
        console.error(loggerPrefix, `Error trying to ${verb} guardrail:`, error);
        setErrMessage(error.message);
        setModal({ type: "error", guardrail: target });
      });
  };

  return (
    <>
      <div className="toolbar btn-group pe-2" role="group" aria-label={gettext("Actions")}>
        <a
          href={guardrail.manifestUrl}
          className="btn btn-icon btn-sm border"
          title={gettext("Chat: Open the guardrail workbench")}
          tabIndex={0}
        >
          <i className="bi bi-chat-dots md-teal" />
        </a>
        <a
          href={guardrail.manifestUrl}
          className="btn btn-icon btn-sm border"
          title={gettext("Edit: Open the YAML manifest that defines this guardrail resource")}
          tabIndex={0}
        >
          <i className="bi bi-pencil-square md-blue" />
        </a>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title={gettext("Clone: Clone this guardrail resource to a new resource owned by you")}
          onClick={() => setModal({ type: "clone", guardrail })}
          tabIndex={0}
        >
          <i className="bi bi-files md-green" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title={gettext("Rename: Rename this guardrail resource")}
          onClick={() => setModal({ type: "rename", guardrail })}
          tabIndex={0}
        >
          <i className="bi bi-pencil md-blue" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title={
            guardrail.canDelete === false
              ? gettext(
                  "Delete: You can't delete this guardrail, because other resources depend on it, or you don't have permission to delete it",
                )
              : gettext("Delete: Delete this guardrail resource")
          }
          onClick={() => setModal({ type: "delete", guardrail })}
          disabled={guardrail.canDelete === false}
          tabIndex={0}
        >
          <i className="bi bi-trash md-red" />
        </button>
      </div>

      <div>
        {modal.type === "clone" && (
          <ModalClone
            guardrail={modal.guardrail}
            onOk={(newName) => runAction(modal.guardrail!, `clone/${modal.guardrail!.id}/${newName}/`, "clone")}
            onCancel={handleCloseModal}
          />
        )}
        {modal.type === "rename" && (
          <ModalRename
            guardrail={modal.guardrail}
            onOk={(newName) => runAction(modal.guardrail!, `rename/${modal.guardrail!.id}/${newName}/`, "rename")}
            onCancel={handleCloseModal}
          />
        )}
        <ModalDelete
          show={modal.type === "delete"}
          guardrail={modal.guardrail}
          onOk={() => runAction(modal.guardrail!, `delete/${modal.guardrail!.id}/`, "delete")}
          onCancel={handleCloseModal}
        />
        <ModalError
          show={modal.type === "error"}
          guardrail={modal.guardrail}
          message={errMessage}
          onClose={handleCloseModal}
        />
        <ModalConfirmation
          show={modal.type === "confirmation"}
          guardrail={modal.guardrail}
          message={successMessage}
          onClose={handleCloseModalWithRequery}
        />
      </div>
    </>
  );
};

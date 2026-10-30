/**
 * Toolbar React Component
 *
 * This component provides a toolbar for managing LLMTool resources, used in the ListView's rows and in the DetailView of a plugin's detail.
 * It offers actions for opening, editing, cloning, renaming, and deleting an LLMTool, with modal dialogs for confirmation and error handling.
 *
 * Features:
 * - Action buttons for: Open (chat), Edit (YAML manifest), Clone, Rename, and Delete LLMTool resources.
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
 * - llmtool (LLMTool): The LLMTool resource to manage.
 *
 * Usage:
 * <Toolbar sessionContext={sessionContext} llmtool={llmtool} onRequery={onRequery} />
 *
 * This component is intended to be embedded in each LLMTool row of the ListView, and in the DetailView.
 */
import { useState } from "react";
import type { SessionContext } from "@smarter/common";
import { actionUrl, fetchDjangoUrl, gettext, interpolate, interpolateNodes, Modal } from "@smarter/common";

import { loggerPrefix } from "@/lib/const";
import type { LLMTool } from "@/lib/Types";
import "@/components/Toolbar/styles.css";

type ModalType = null | "clone" | "rename" | "delete" | "confirmation" | "error";

interface NameModalProps {
  llmtool: LLMTool | null;
  onOk: (newName: string) => void;
  onCancel: () => void;
}

/** Asks for the name of the clone. It is mounted only while open, so it starts empty. */
const ModalClone = ({ llmtool, onOk, onCancel }: NameModalProps) => {
  const [inputValue, setInputValue] = useState("");
  return (
    <Modal show title={gettext("Clone LLMTool")} onOk={() => onOk(inputValue)} onCancel={onCancel}>
      <p>
        {interpolateNodes(gettext("Clone LLMTool %(name)s to a new resource owned by you."), {
          name: <strong>{llmtool?.name}</strong>,
        })}
      </p>
      <p>
        <em>{gettext("Provide the new name for the cloned LLMTool.")}</em>
      </p>
      <input
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        placeholder={gettext("Enter new LLMTool name")}
      />
    </Modal>
  );
};

/** Asks for the new name. It is mounted only while open, so it starts with the current name. */
const ModalRename = ({ llmtool, onOk, onCancel }: NameModalProps) => {
  const [inputValue, setInputValue] = useState(llmtool?.name || "");
  return (
    <Modal show title={gettext("Rename LLMTool")} onOk={() => onOk(inputValue)} onCancel={onCancel}>
      <p>{interpolateNodes(gettext("Rename LLMTool %(name)s."), { name: <strong>{llmtool?.name}</strong> })}</p>
      <p>
        <em>{gettext("Provide the new name for the LLMTool.")}</em>
      </p>
      <input
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        placeholder={gettext("Enter new LLMTool name")}
      />
    </Modal>
  );
};

/** Confirms the deletion. */
const ModalDelete = ({
  show,
  llmtool,
  onOk,
  onCancel,
}: {
  show: boolean;
  llmtool: LLMTool | null;
  onOk: () => void;
  onCancel: () => void;
}) => (
  <Modal show={show} title={gettext("Delete LLMTool")} onOk={onOk} onCancel={onCancel}>
    <p>
      {interpolateNodes(gettext("Are you sure you want to delete LLMTool %(name)s?"), {
        name: <strong>{llmtool?.name}</strong>,
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
  llmtool,
  message,
  onClose,
}: {
  show: boolean;
  llmtool: LLMTool | null;
  message: string;
  onClose: () => void;
}) => (
  <Modal show={show} title={gettext("❌ Error")} onClose={onClose}>
    <p>
      {interpolateNodes(gettext("An error occurred while performing the operation on LLMTool %(name)s."), {
        name: <strong>{llmtool?.name}</strong>,
      })}
    </p>
    <p>{message ? <span className="text-danger">{message}</span> : <em>{gettext("An unknown error occurred.")}</em>}</p>
  </Modal>
);

/** Confirms that the operation succeeded. */
const ModalConfirmation = ({
  show,
  llmtool,
  message,
  onClose,
}: {
  show: boolean;
  llmtool: LLMTool | null;
  message: string;
  onClose: () => void;
}) => (
  <Modal show={show} title={gettext("✅ Success")} onClose={onClose}>
    <p>
      {message} <strong>{llmtool?.name}</strong>.
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
        failed: gettext("Failed to clone LLMTool (%(status)s): %(error)s"),
        succeeded: gettext("Successfully cloned LLMTool"),
      };
    case "rename":
      return {
        failed: gettext("Failed to rename LLMTool (%(status)s): %(error)s"),
        succeeded: gettext("Successfully renamed LLMTool"),
      };
    default:
      return {
        failed: gettext("Failed to delete LLMTool (%(status)s): %(error)s"),
        succeeded: gettext("Successfully deleted LLMTool"),
      };
  }
};

interface ToolbarProps {
  sessionContext: SessionContext;
  llmtool: LLMTool;
  onRequery: () => void;
}

export const Toolbar = ({ sessionContext, llmtool, onRequery }: ToolbarProps) => {
  // this is a single way to control which and whether a modal is open.
  // it ensures that only one modal can be open at a time.
  const [modal, setModal] = useState<{ type: ModalType; llmtool: LLMTool | null }>({ type: null, llmtool: null });
  const [errMessage, setErrMessage] = useState<string>("");
  const [successMessage, setSuccessMessage] = useState<string>("");

  const handleCloseModal = () => {
    setModal({ type: null, llmtool: null });
  };
  const handleCloseModalWithRequery = () => {
    setModal({ type: null, llmtool: null });
    onRequery();
  };

  /**
   * POST to one of the list API's actions, e.g. clone/12/new_name/, and show the result: the
   * confirmation modal on success, else the error modal with the server's error message.
   * See actionUrl() in @smarter/common for how the action's URL is built.
   */
  const runAction = (target: LLMTool, path: string, verb: "clone" | "rename" | "delete") => {
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
        console.debug(loggerPrefix, `Successfully ${verb}d LLMTool:`, data);
        setSuccessMessage(actionMessages(verb).succeeded);
        // clone and rename return the resulting LLMTool; delete returns a message.
        setModal({ type: "confirmation", llmtool: data && data.id ? (data as LLMTool) : target });
      })
      .catch((error) => {
        console.error(loggerPrefix, `Error trying to ${verb} LLMTool:`, error);
        setErrMessage(error.message);
        setModal({ type: "error", llmtool: target });
      });
  };

  return (
    <>
      <div className="toolbar btn-group pe-2" role="group" aria-label={gettext("Actions")}>
        <a
          href={llmtool.manifestUrl}
          className="btn btn-icon btn-sm border"
          title={gettext("Chat: Open the LLMTool workbench")}
          tabIndex={0}
        >
          <i className="bi bi-chat-dots md-teal" />
        </a>
        <a
          href={llmtool.manifestUrl}
          className="btn btn-icon btn-sm border"
          title={gettext("Edit: Open the YAML manifest that defines this LLMTool resource")}
          tabIndex={0}
        >
          <i className="bi bi-pencil-square md-blue" />
        </a>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title={gettext("Clone: Clone this LLMTool resource to a new resource owned by you")}
          onClick={() => setModal({ type: "clone", llmtool })}
          tabIndex={0}
        >
          <i className="bi bi-files md-green" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title={gettext("Rename: Rename this LLMTool resource")}
          onClick={() => setModal({ type: "rename", llmtool })}
          tabIndex={0}
        >
          <i className="bi bi-pencil md-blue" />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-sm border"
          title={
            llmtool.canDelete === false
              ? gettext(
                  "Delete: You can't delete this LLMTool, because other resources depend on it, or you don't have permission to delete it",
                )
              : gettext("Delete: Delete this LLMTool resource")
          }
          onClick={() => setModal({ type: "delete", llmtool })}
          disabled={llmtool.canDelete === false}
          tabIndex={0}
        >
          <i className="bi bi-trash md-red" />
        </button>
      </div>

      <div>
        {modal.type === "clone" && (
          <ModalClone
            llmtool={modal.llmtool}
            onOk={(newName) => runAction(modal.llmtool!, `clone/${modal.llmtool!.id}/${newName}/`, "clone")}
            onCancel={handleCloseModal}
          />
        )}
        {modal.type === "rename" && (
          <ModalRename
            llmtool={modal.llmtool}
            onOk={(newName) => runAction(modal.llmtool!, `rename/${modal.llmtool!.id}/${newName}/`, "rename")}
            onCancel={handleCloseModal}
          />
        )}
        <ModalDelete
          show={modal.type === "delete"}
          llmtool={modal.llmtool}
          onOk={() => runAction(modal.llmtool!, `delete/${modal.llmtool!.id}/`, "delete")}
          onCancel={handleCloseModal}
        />
        <ModalError
          show={modal.type === "error"}
          llmtool={modal.llmtool}
          message={errMessage}
          onClose={handleCloseModal}
        />
        <ModalConfirmation
          show={modal.type === "confirmation"}
          llmtool={modal.llmtool}
          message={successMessage}
          onClose={handleCloseModalWithRequery}
        />
      </div>
    </>
  );
};

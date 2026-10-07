/**
 * Modal Component
 *
 * A reusable modal dialogue for React applications. Displays a modal overlay with a title, optional input, and customizable content.
 *
 * Props:
 * - show (boolean): Controls visibility of the modal.
 * - title (string): Title text displayed in the modal header.
 * - children (React.ReactNode): Content to render inside the modal body.
 * - inputLabel (string, optional): If provided, displays a labeled input field.
 * - onClose (function, optional): Handler for closing the modal (overlay click, Close button, or close icon).
 * - onOk (function, optional): Handler for the OK button.
 * - onCancel (function, optional): Handler for the Cancel button.
 *
 * At least one of onClose, onOk, or onCancel must be provided.
 *
 * Usage:
 * <Modal show={show} title="My Modal" onClose={handleClose} onOk={handleOk}>
 *   <p>Modal content goes here.</p>
 * </Modal>
 */
import React, { useEffect, useId } from "react";

export function Modal({
  show,
  title,
  children,
  inputLabel,
  onClose,
  onOk,
  onCancel,
}: {
  show: boolean;
  title: string;
  children?: React.ReactNode;
  inputLabel?: string;
  onClose?: () => void;
  onOk?: () => void;
  onCancel?: () => void;
}) {
  const titleId = useId();

  useEffect(() => {
    if (!show || !onOk) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Enter") {
        e.preventDefault();
        onOk();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [show, onOk]);

  // Escape closes the dialog, as clicking outside it does: the keyboard's way to dismiss it.
  const dismiss = onClose || onCancel;
  useEffect(() => {
    if (!show || !dismiss) return;
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") dismiss();
    };
    window.addEventListener("keydown", handleEscape);
    return () => window.removeEventListener("keydown", handleEscape);
  }, [show, dismiss]);

  if (!onClose && !onOk && !onCancel) {
    throw new Error("Modal requires at least one of onClose, onOk, or onCancel handlers.");
  }
  const handleClose = onClose || onCancel;
  if (!handleClose) {
    throw new Error("Modal requires at least one of onClose, onOk, or onCancel handlers.");
  }

  if (!show) return null;

  return (
    // Clicking the backdrop closes the dialog: a mouse convenience, whose keyboard equivalent is
    // Escape (see above), so the click handlers need no key handlers of their own.
    // eslint-disable-next-line jsx-a11y/click-events-have-key-events, jsx-a11y/no-noninteractive-element-interactions
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      className="modal show"
      style={{
        display: "block",
        position: "fixed",
        inset: 0,
        backgroundColor: "rgba(0,0,0,0.5)",
        zIndex: 1050,
      }}
      tabIndex={-1}
      onClick={handleClose}
    >
      {/* eslint-disable-next-line jsx-a11y/click-events-have-key-events, jsx-a11y/no-static-element-interactions -- keeps clicks inside the dialog from closing it. */}
      <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="modal-content">
          <div className="modal-header">
            <h5 className="modal-title" id={titleId}>
              {title}
            </h5>

            {onClose && <button type="button" className="btn-close" aria-label="Close" onClick={onClose} />}
          </div>

          {inputLabel && (
            <div className="modal-input">
              <label>{inputLabel}</label>
              <input type="text" className="form-control" />
            </div>
          )}

          <div className="modal-body">{children}</div>

          <div className="modal-footer">
            {onClose && (
              <button type="button" className="btn btn-secondary" onClick={onClose}>
                Close
              </button>
            )}

            {onOk && (
              <button type="button" className="btn btn-primary" onClick={onOk}>
                OK
              </button>
            )}

            {onCancel && (
              <button type="button" className="btn btn-secondary" onClick={onCancel}>
                Cancel
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

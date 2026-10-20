/**
 * useDropdown: how a menu that a button opens opens and closes, for the console's menus, e.g. the user menu
 * (@smarter/dashboard-user-menu) and the workbench's Help menu (@smarter/workbench). Each draws its own menu.
 *
 * The button toggles the menu. A click outside the root element, which holds the button and the menu, closes it,
 * and so does Escape, which also returns the focus to the button. A menu item that runs an action calls close().
 *
 * Usage:
 *
 *   const { open, toggle, close, rootRef, buttonRef, menuId } = useDropdown();
 *   <div ref={rootRef}>
 *     <button ref={buttonRef} aria-expanded={open} aria-controls={menuId} onClick={toggle}>Help</button>
 *     <div id={menuId} hidden={!open}>...</div>
 *   </div>
 */
import { useCallback, useEffect, useId, useRef, useState } from "react";

export function useDropdown<Root extends HTMLElement = HTMLDivElement>() {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<Root>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const menuId = useId();

  useEffect(() => {
    if (!open) return;
    const handlePointerDown = (event: MouseEvent) => {
      if (event.target instanceof Node && !rootRef.current?.contains(event.target)) setOpen(false);
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      setOpen(false);
      buttonRef.current?.focus();
    };
    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  const toggle = useCallback(() => setOpen((previous) => !previous), []);
  const close = useCallback(() => setOpen(false), []);

  return { open, setOpen, toggle, close, rootRef, buttonRef, menuId };
}

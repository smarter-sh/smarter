/**
 * The workbench's Help menu, in the chat's header: the Help button opens a list of the workbench's help, the Docs
 * dialog (in sandbox mode only, with onDocs) and the guided tour. The two were buttons of their own, beside the
 * chat's buttons that are used throughout a session, until the header ran out of room.
 *
 * It is a disclosure, not an ARIA menu: the button says whether the list is expanded, and the list's items are
 * ordinary buttons, after it in the tab order. A click outside the menu, or Escape, closes it. See useDropdown in
 * @smarter/common.
 *
 * :param onDocs: Opens the Docs dialog. Without it, the menu has no Docs item.
 * :param onTour: Starts the guided tour.
 */
import { gettext, useDropdown } from "@smarter/common";
import { HeaderButton } from "@smarter.sh/ui-chat";

import { DocsIcon, HelpIcon, TourIcon } from "@/components/icons";
import "@/components/HelpMenu/styles.css";

interface HelpMenuProps {
  onDocs?: () => void;
  onTour: () => void;
}

export default function HelpMenu({ onDocs, onTour }: HelpMenuProps) {
  const { open, toggle, close, rootRef, buttonRef, menuId } = useDropdown();

  /** A menu item closes the menu, then runs its action, which opens a dialog. */
  const run = (action: () => void) => () => {
    close();
    action();
  };

  return (
    <div ref={rootRef} className="smarter-workbench-help">
      <HeaderButton
        ref={buttonRef}
        className="smarter-workbench-help-button"
        icon={<HelpIcon />}
        onClick={toggle}
        title={gettext("The documentation, and a guided tour of the workbench")}
        aria-expanded={open}
        aria-controls={menuId}
      >
        {/* Translators: the button that opens the workbench's Help menu. */}
        {gettext("Help")}
      </HeaderButton>
      {open && (
        <ul id={menuId} className="smarter-workbench-help-menu">
          {onDocs && (
            <li>
              <button
                type="button"
                className="smarter-workbench-help-item smarter-workbench-docs-button"
                onClick={run(onDocs)}
                aria-haspopup="dialog"
              >
                <DocsIcon />
                <span>
                  {/* Translators: the Help menu's item that opens the dialog of links to the documentation. */}
                  {gettext("Technical references")}
                </span>
              </button>
            </li>
          )}
          <li>
            <button
              type="button"
              className="smarter-workbench-help-item smarter-workbench-tour-button"
              onClick={run(onTour)}
              aria-haspopup="dialog"
            >
              <TourIcon />
              <span>
                {/* Translators: the Help menu's item that starts the guided tour of the workbench. */}
                {gettext("Take the guided tour")}
              </span>
            </button>
          </li>
        </ul>
      )}
    </div>
  );
}

/**
 * The Docs dialog: links to the technical references for prompt engineers and software engineers
 * who build LLMClients, and the applications that host them. SmarterChat opens it from its Docs
 * button, which is displayed only in sandbox mode.
 *
 * The links are grouped into a tab for each audience, and the first tab, Prompt Engineer, is
 * selected when it opens. The arrow, Home and End keys move between the tabs. It is a modal: Escape, the close button, and a click outside of it all close it. The links open
 * in a new tab.
 */
import { useEffect, useRef, useState, type KeyboardEvent as ReactKeyboardEvent } from "react";

import { docSections, type DocSection } from "@/components/DocsDialog/data";
import { gettext } from "@smarter/common";
import "@/components/DocsDialog/styles.css";

interface DocsDialogProps {
  onClose: () => void;
  sections?: DocSection[];
}

function DocsDialog({ onClose, sections = docSections() }: DocsDialogProps) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const [selected, setSelected] = useState(0);

  useEffect(() => {
    closeRef.current?.focus();
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    // a click outside of the dialog, e.g. on its backdrop, closes it. The event's path, rather than its target,
    // because a document listener sees a click in a shadow root, e.g. the embed script's, as a click on its host.
    const handleMouseDown = (event: MouseEvent) => {
      const dialog = dialogRef.current;
      if (dialog && !event.composedPath().includes(dialog)) onClose();
    };
    document.addEventListener("keydown", handleKeyDown);
    document.addEventListener("mousedown", handleMouseDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.removeEventListener("mousedown", handleMouseDown);
    };
  }, [onClose]);

  const selectTab = (index: number) => {
    setSelected(index);
    tabRefs.current[index]?.focus();
  };

  const handleTabKeyDown = (event: ReactKeyboardEvent<HTMLButtonElement>) => {
    const last = sections.length - 1;
    const moves: Record<string, number> = {
      ArrowLeft: selected === 0 ? last : selected - 1,
      ArrowRight: selected === last ? 0 : selected + 1,
      Home: 0,
      End: last,
    };
    if (event.key in moves) {
      event.preventDefault();
      selectTab(moves[event.key]);
    }
  };

  const section = sections[selected];

  return (
    <div className="smarter-chat-docs-backdrop">
      <div
        ref={dialogRef}
        className="smarter-chat-docs-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="smarter-chat-docs-title"
      >
        <div className="smarter-chat-docs-header">
          <h2 id="smarter-chat-docs-title">{gettext("Docs")}</h2>
          <button
            ref={closeRef}
            type="button"
            className="smarter-chat-docs-close"
            onClick={onClose}
            aria-label={gettext("Close")}
            title={gettext("Close")}
          >
            &times;
          </button>
        </div>
        <p className="smarter-chat-docs-intro">
          {gettext("Technical references for building LLMClients, and the applications that host them.")}
        </p>
        <div className="smarter-chat-docs-tabs" role="tablist" aria-label={gettext("Audience")}>
          {sections.map((tab, index) => (
            <button
              key={tab.title}
              ref={(element) => {
                tabRefs.current[index] = element;
              }}
              type="button"
              role="tab"
              id={`smarter-chat-docs-tab-${index}`}
              className="smarter-chat-docs-tab"
              aria-selected={index === selected}
              aria-controls="smarter-chat-docs-panel"
              tabIndex={index === selected ? 0 : -1}
              onClick={() => setSelected(index)}
              onKeyDown={handleTabKeyDown}
            >
              {tab.title}
            </button>
          ))}
        </div>
        {section && (
          <div
            className="smarter-chat-docs-panel"
            role="tabpanel"
            id="smarter-chat-docs-panel"
            aria-labelledby={`smarter-chat-docs-tab-${selected}`}
          >
            <p className="smarter-chat-docs-section-description">{section.description}</p>
            <ul className="smarter-chat-docs-list">
              {section.links.map((link) => (
                <li key={link.url}>
                  <a href={link.url} target="_blank" rel="noopener noreferrer">
                    {link.title}
                  </a>
                  <span className="smarter-chat-docs-description">{link.description}</span>
                  <span className="smarter-chat-docs-url">{link.url}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

export default DocsDialog;

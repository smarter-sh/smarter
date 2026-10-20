/**
 * The top of a hint's note: an icon badge, if the hint has one, then a small eyebrow, e.g. Step 3 of 13, and
 * the title, or the text of a note without a title.
 *
 * :param icon: A Keen icon's class, e.g. ki-rocket, from the web console's Keen theme.
 * :param eyebrow: Above the title, in small capitals.
 * :param id: The id of the title, which labels the note.
 * :param title: The title.
 * :param titleClassName: The class of the title, e.g. the text's, for a note whose text is its title.
 */
import type { ReactNode } from "react";

import "../styles.css";

interface NoteHeaderProps {
  icon?: string;
  eyebrow?: ReactNode;
  id: string;
  title: ReactNode;
  titleClassName?: string;
}

function NoteHeader({ icon, eyebrow, id, title, titleClassName = "smarter-onboarding-note-title" }: NoteHeaderProps) {
  return (
    <div className="smarter-onboarding-note-header">
      {icon && (
        <span className="smarter-onboarding-note-icon" aria-hidden="true">
          <i className={`ki-outline ${icon}`}></i>
        </span>
      )}
      <div className="smarter-onboarding-note-heading">
        {eyebrow && <div className="smarter-onboarding-note-eyebrow">{eyebrow}</div>}
        <div id={id} className={titleClassName}>
          {title}
        </div>
      </div>
    </div>
  );
}

export default NoteHeader;

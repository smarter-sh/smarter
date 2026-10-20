/**
 * A Did you know? note: its title, a fact, and the fact's link, if it has one.
 *
 * It has no styles of its own. Each consumer styles it with classNames, as the welcome dialog's card
 * and the web console's title bar do, and may give it an icon before the title and after the link.
 * The link opens in a new tab. The fact's text is also its title, so that a consumer that cuts it short
 * still shows it in full on hover.
 *
 * :param fact: The fact.
 * :param classNames: The class names of the note's root, title, text and link.
 * :param icon: Shown before the title, e.g. a Keen icon.
 * :param linkIcon: Shown after the link's label, e.g. a Keen icon for an external link.
 */
import type { ReactNode } from "react";
import { gettext } from "@smarter/common";

import type { DidYouKnowFact } from "../../lib/facts";

export interface DidYouKnowClassNames {
  root?: string;
  title?: string;
  text?: string;
  link?: string;
}

export interface DidYouKnowProps {
  fact: DidYouKnowFact;
  classNames?: DidYouKnowClassNames;
  icon?: ReactNode;
  linkIcon?: ReactNode;
}

function DidYouKnow({ fact, classNames = {}, icon, linkIcon }: DidYouKnowProps) {
  const title = gettext("Did you know?");
  return (
    <aside className={classNames.root} aria-label={title}>
      <span className={classNames.title}>
        {icon}
        {title}
      </span>{" "}
      <span className={classNames.text} title={fact.text}>
        {fact.text}
      </span>
      {fact.link && (
        <>
          {" "}
          <a href={fact.link.url} className={classNames.link} target="_blank" rel="noopener noreferrer">
            {fact.link.label}
            {linkIcon}
          </a>
        </>
      )}
    </aside>
  );
}

export default DidYouKnow;

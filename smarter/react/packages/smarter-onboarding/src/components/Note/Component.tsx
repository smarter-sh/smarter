/**
 * A hint's note: a small card beside the element that it points to, or in the middle of the window when it
 * points to none. It measures itself, and placeNote() keeps it inside the window. Beside an element, its arrow
 * points at the element.
 *
 * :param box: The box of the element, or null for the middle of the window.
 * :param modal: Whether the note is a modal dialog, as the tour's is, or a non-modal one, as the spotlight's.
 * :param labelledBy: The id of the note's title, or its text.
 * :param describedBy: The id of the note's text, if it has a title.
 * :param children: The note's content.
 */
import { useLayoutEffect, useRef, useState, type CSSProperties, type ReactNode } from "react";

import { arrowOffset, placeNote, type Box, type Placement } from "../../lib/position";
import "../styles.css";

interface NoteProps {
  box: Box | null;
  modal?: boolean;
  labelledBy: string;
  describedBy?: string;
  children: ReactNode;
}

function Note({ box, modal = false, labelledBy, describedBy, children }: NoteProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 320, height: 160 });

  // the note's size changes with its text, e.g. from one step of a tour to the next.
  useLayoutEffect(() => {
    const element = ref.current;
    if (!element) return;
    const measure = () => {
      const rect = element.getBoundingClientRect();
      if (rect.width === 0) return;
      setSize((previous) =>
        previous.width === rect.width && previous.height === rect.height
          ? previous
          : { width: rect.width, height: rect.height },
      );
    };
    measure();
    if (typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const viewport = { width: window.innerWidth, height: window.innerHeight };
  const position = box
    ? placeNote(box, size, viewport)
    : {
        top: Math.max(8, (viewport.height - size.height) / 2),
        left: Math.max(8, (viewport.width - size.width) / 2),
        placement: "center",
      };

  const style: CSSProperties & { "--smarter-onboarding-arrow"?: string } = { top: position.top, left: position.left };
  if (box && position.placement !== "center") {
    const offset = arrowOffset(box, position, size, position.placement as Placement);
    style["--smarter-onboarding-arrow"] = `${offset}px`;
  }

  return (
    <div
      ref={ref}
      className={`smarter-onboarding-note smarter-onboarding-note-${position.placement}`}
      style={style}
      role="dialog"
      aria-modal={modal}
      aria-labelledby={labelledBy}
      aria-describedby={describedBy}
    >
      {children}
    </div>
  );
}

export default Note;

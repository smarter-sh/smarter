/**
 * A spotlight: a sparkling ring around one element, e.g. the sidebar's LLM Clients link, and a short note
 * beside it with a Got it button. The page stays usable, and the element clickable.
 *
 * A click on the element is "clicked", and Got it or Escape is "dismissed". Either way, onDone is called once.
 * While the element is off screen, e.g. when the window scrolls it out of view, the spotlight waits.
 *
 * :param target: The element.
 * :param title: The note's title, if it has one.
 * :param text: The note's text.
 * :param icon: A Keen icon's class for the note's badge, e.g. ki-rocket. By default, ki-star.
 * :param buttonLabel: The button's label, by default Got it.
 * :param onDone: Called with what the user did.
 */
import { useCallback, useEffect, useId, useLayoutEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { gettext } from "@smarter/common";

import { OnboardingOutcomes } from "../../lib/const";
import { padBox } from "../../lib/position";
import { useTargetBox } from "../../lib/useTargetBox";
import Note from "../Note/Component";
import NoteHeader from "../Note/Header";
import Ring from "../Ring/Component";
import "../styles.css";

export type SpotlightOutcome = typeof OnboardingOutcomes.CLICKED | typeof OnboardingOutcomes.DISMISSED;

export interface SpotlightProps {
  target: HTMLElement;
  title?: string;
  text: string;
  icon?: string;
  buttonLabel?: string;
  onDone: (outcome: SpotlightOutcome) => void;
}

const RING_PADDING = 6;

function Spotlight({ target, title, text, icon = "ki-star", buttonLabel, onDone }: SpotlightProps) {
  const box = useTargetBox(target);
  const titleId = useId();
  const textId = useId();
  const done = useRef(false);
  const onDoneRef = useRef(onDone);
  useEffect(() => {
    onDoneRef.current = onDone;
  }, [onDone]);

  const finish = useCallback((outcome: SpotlightOutcome) => {
    if (done.current) return;
    done.current = true;
    onDoneRef.current(outcome);
  }, []);

  // a layout effect, so that the element is listened to from the moment the note shows.
  useLayoutEffect(() => {
    const handleClick = () => finish(OnboardingOutcomes.CLICKED);
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") finish(OnboardingOutcomes.DISMISSED);
    };
    target.addEventListener("click", handleClick);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      target.removeEventListener("click", handleClick);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [target, finish]);

  if (!box) return null;
  return createPortal(
    <>
      <Ring box={padBox(box, RING_PADDING)} shape="pill" />
      <Note
        box={padBox(box, RING_PADDING)}
        labelledBy={title ? titleId : textId}
        describedBy={title ? textId : undefined}
      >
        {title ? (
          <>
            <NoteHeader icon={icon} id={titleId} title={title} />
            <p id={textId} className="smarter-onboarding-note-text">
              {text}
            </p>
          </>
        ) : (
          <NoteHeader icon={icon} id={textId} title={text} titleClassName="smarter-onboarding-note-lead" />
        )}
        <div className="smarter-onboarding-note-actions">
          <button
            type="button"
            className="btn btn-sm smarter-onboarding-primary"
            onClick={() => finish(OnboardingOutcomes.DISMISSED)}
          >
            {buttonLabel ?? gettext("Got it")}
          </button>
        </div>
      </Note>
    </>,
    document.body,
  );
}

export default Spotlight;

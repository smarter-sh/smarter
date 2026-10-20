/**
 * A guided tour: a few steps, each a note about one part of the page, with a sparkling ring around it while
 * the rest of the page is dimmed, or a note in the middle of the window for a step about the whole page.
 *
 * It is a modal dialog. Next and Back, and the left and right arrow keys, move between the steps, and Tab
 * keeps the focus inside the note. Skip tour and Escape end it as "dismissed", and the last step's Done as
 * "completed". A step whose element isn't on the page when the tour starts, e.g. a Console tab that this
 * LLMClient doesn't have, is left out, and the steps are counted without it. The steps are picked when the
 * tour mounts, so a page that shows a part of itself for the tour, e.g. opens the Console, does so first.
 *
 * A step with activate clicks its element when it shows, e.g. a tab, so that the page shows what the step is
 * about, not only the control that leads to it.
 *
 * :param steps: The steps, in order.
 * :param onFinish: Called once, with how the tour ended.
 */
import { useEffect, useId, useRef, useState, type KeyboardEvent as ReactKeyboardEvent } from "react";
import { createPortal } from "react-dom";
import { gettext, interpolate } from "@smarter/common";

import { OnboardingOutcomes } from "../../lib/const";
import { padBox } from "../../lib/position";
import { findTarget } from "../../lib/targets";
import { useTargetBox } from "../../lib/useTargetBox";
import Note from "../Note/Component";
import NoteHeader from "../Note/Header";
import Ring from "../Ring/Component";
import "../styles.css";

export interface TourStep {
  /** The css selector of the element that the step is about, or none for a step about the whole page. */
  target?: string;
  /** A Keen icon's class for the note's badge, e.g. ki-rocket, from the web console's Keen theme. */
  icon?: string;
  /**
   * Whether the step clicks its element when it shows, e.g. a tab, which then shows its content. Only for an
   * element whose click shows something, and changes nothing else.
   */
  activate?: boolean;
  title: string;
  text: string;
}

export type TourOutcome = typeof OnboardingOutcomes.COMPLETED | typeof OnboardingOutcomes.DISMISSED;

export interface TourProps {
  steps: TourStep[];
  onFinish: (outcome: TourOutcome) => void;
}

const RING_PADDING = 8;
const FOCUSABLE = "button:not([disabled]), a[href]";

interface AvailableStep {
  step: TourStep;
  element: HTMLElement | null;
}

/** The steps whose element is on the page, and the elements. */
function availableSteps(steps: TourStep[]): AvailableStep[] {
  return steps.flatMap<AvailableStep>((step) => {
    if (!step.target) return [{ step, element: null }];
    const element = findTarget(step.target);
    return element ? [{ step, element }] : [];
  });
}

function Tour({ steps, onFinish }: TourProps) {
  const [available] = useState(() => availableSteps(steps));
  const [index, setIndex] = useState(0);
  const titleId = useId();
  const textId = useId();
  const noteRef = useRef<HTMLDivElement>(null);
  const primaryRef = useRef<HTMLButtonElement>(null);
  const finished = useRef(false);
  const last = available.length - 1;
  const current = available[index];
  const box = useTargetBox(current?.element ?? null);

  const finish = (outcome: TourOutcome) => {
    if (finished.current) return;
    finished.current = true;
    onFinish(outcome);
  };

  useEffect(() => {
    if (available.length === 0) finish(OnboardingOutcomes.COMPLETED);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- once, when the tour starts.
  }, []);

  useEffect(() => {
    if (current?.step.activate) current.element?.click();
    current?.element?.scrollIntoView?.({ block: "nearest", inline: "nearest" });
    primaryRef.current?.focus();
  }, [current]);

  if (!current) return null;

  const goTo = (next: number) => setIndex(Math.max(0, Math.min(last, next)));

  const handleKeyDown = (event: ReactKeyboardEvent<HTMLDivElement>) => {
    if (event.key === "Escape") {
      event.preventDefault();
      finish(OnboardingOutcomes.DISMISSED);
    } else if (event.key === "ArrowRight") {
      event.preventDefault();
      goTo(index + 1);
    } else if (event.key === "ArrowLeft") {
      event.preventDefault();
      goTo(index - 1);
    } else if (event.key === "Tab") {
      const focusable = Array.from(noteRef.current?.querySelectorAll<HTMLElement>(FOCUSABLE) ?? []);
      if (focusable.length === 0) return;
      const first = focusable[0];
      const end = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        end.focus();
      } else if (!event.shiftKey && document.activeElement === end) {
        event.preventDefault();
        first.focus();
      }
    }
  };

  const ring = box ? padBox(box, RING_PADDING) : null;
  return createPortal(
    <>
      {/* blocks the page while the tour is open. With a ring, the ring dims the page around it. */}
      <div className={`smarter-onboarding-blocker ${ring ? "" : "smarter-onboarding-blocker-dim"}`} />
      {ring && <Ring box={ring} shape="rounded" dim />}
      {/* eslint-disable-next-line jsx-a11y/no-static-element-interactions -- the tour handles its own keys: Escape, the arrows and Tab. */}
      <div ref={noteRef} onKeyDown={handleKeyDown}>
        <Note key={index} box={ring} modal labelledBy={titleId} describedBy={textId}>
          <NoteHeader
            icon={current.step.icon}
            eyebrow={interpolate(gettext("Step %(step)s of %(steps)s"), { step: index + 1, steps: available.length })}
            id={titleId}
            title={current.step.title}
          />
          <div className="smarter-onboarding-progress" aria-hidden="true">
            <div
              className="smarter-onboarding-progress-bar"
              style={{ width: `${((index + 1) / available.length) * 100}%` }}
            />
          </div>
          <p id={textId} className="smarter-onboarding-note-text">
            {current.step.text}
          </p>
          <div className="smarter-onboarding-note-actions">
            {index === 0 ? (
              <button
                type="button"
                className="btn btn-sm btn-link text-muted"
                onClick={() => finish(OnboardingOutcomes.DISMISSED)}
              >
                {gettext("Skip tour")}
              </button>
            ) : (
              <button type="button" className="btn btn-sm btn-light" onClick={() => goTo(index - 1)}>
                {gettext("Back")}
              </button>
            )}
            {index < last ? (
              <button
                ref={primaryRef}
                type="button"
                className="btn btn-sm smarter-onboarding-primary"
                onClick={() => goTo(index + 1)}
              >
                {gettext("Next")}
              </button>
            ) : (
              <button
                ref={primaryRef}
                type="button"
                className="btn btn-sm smarter-onboarding-primary"
                onClick={() => finish(OnboardingOutcomes.COMPLETED)}
              >
                {gettext("Done")}
              </button>
            )}
          </div>
        </Note>
      </div>
    </>,
    document.body,
  );
}

export default Tour;

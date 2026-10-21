/**
 * DidYouKnow dashboard widget.
 *
 * This component renders the fact of the day, a piece of trivia about The Smarter Project from
 * @smarter/didyouknow, as a slim card: a lightbulb, Did you know?, the fact, and its link. The fact
 * of the day is the same for everyone, from midnight to midnight UTC, and is the one that the note
 * below the web console's title shows, so smarter.sh and the web console show the same fact.
 *
 * :param date: The moment whose day picks the fact. Now, by default.
 * :type date: Date
 * :returns: A JSX element containing the Did you know? card.
 * :rtype: JSX.Element
 *
 * :example:
 *
 *     <DidYouKnow />
 */
import "./styles.css";
import { DidYouKnow as DidYouKnowNote, factOfTheDay } from "@smarter/didyouknow";

export interface DidYouKnowProps {
  /** The moment whose day picks the fact. */
  date?: Date;
}

/** A lightbulb, inlined, as the widgets' other icons are. */
const Lightbulb = () => (
  <svg
    className="didyouknow-icon"
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    width="20"
    height="20"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    <path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5" />
    <path d="M9 18h6" />
    <path d="M10 22h4" />
  </svg>
);

function DidYouKnow({ date = new Date() }: DidYouKnowProps) {
  return (
    <DidYouKnowNote
      fact={factOfTheDay(date)}
      classNames={{
        root: "card border-transparent didyouknow-card",
        title: "didyouknow-title",
        text: "didyouknow-text",
        link: "didyouknow-link",
      }}
      icon={<Lightbulb />}
    />
  );
}

export default DidYouKnow;

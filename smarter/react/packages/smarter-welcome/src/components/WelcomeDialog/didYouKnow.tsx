/**
 * The welcome dialog's Did you know? note: a fact from @smarter/didyouknow, which the dialog shows
 * below the illustration of one of its steps. Each time the dialog opens, it picks the step and the
 * fact at random.
 */
import { didYouKnowFacts, type DidYouKnowFact } from "@smarter/didyouknow";

/** The step whose illustration shows the note, and the fact that it shows. */
export interface DidYouKnow {
  step: number;
  fact: DidYouKnowFact;
}

/**
 * Picks the step and the fact at random.
 *
 * :param stepCount: The number of the dialog's steps.
 * :param random: A function that returns a number from 0 up to, but not including, 1.
 * :returns: The step's index and the fact.
 */
export function pickDidYouKnow(stepCount: number, random: () => number = Math.random): DidYouKnow {
  const facts = didYouKnowFacts();
  return {
    step: Math.floor(random() * stepCount),
    fact: facts[Math.floor(random() * facts.length)],
  };
}

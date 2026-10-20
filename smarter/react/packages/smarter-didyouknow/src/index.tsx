/**
 * @smarter/didyouknow: Did you know? trivia about The Smarter Project, for the welcome dialog
 * (@smarter/welcome) and the note below the web console's title (this package's own app, main.tsx).
 */
export { default as DidYouKnow } from "./components/DidYouKnow/Component";
export type { DidYouKnowClassNames, DidYouKnowProps } from "./components/DidYouKnow/Component";
export { didYouKnowFacts, factOfTheDay, randomFact } from "./lib/facts";
export type { DidYouKnowFact } from "./lib/facts";

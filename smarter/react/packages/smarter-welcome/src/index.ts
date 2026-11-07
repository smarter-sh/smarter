/**
 * The welcome dialog, as a component, for the single-page console (@smarter/console), which renders it in its
 * frame from the console's session (src/lib/welcome.ts there). main.tsx renders it on the package's development
 * page, from src/mocks/fixtures.ts.
 *
 * The package's source uses relative imports, so that another package's build can import it.
 */
export { default as Welcome, OPEN_ATTRIBUTE as WELCOME_OPEN_ATTRIBUTE } from "./App";
export type { AppContext as WelcomeContext } from "./lib/Types";

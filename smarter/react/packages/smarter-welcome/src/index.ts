/**
 * The welcome dialog, as a component, for the single-page console (@smarter/console), which renders it in its
 * frame from the console's session. main.tsx mounts it on the pages that Django still renders, from the attributes
 * of templates/react/welcome.html.
 *
 * The package's source uses relative imports, so that another package's build can import it.
 */
export { default as Welcome, OPEN_ATTRIBUTE as WELCOME_OPEN_ATTRIBUTE } from "./App";
export type { AppContext as WelcomeContext } from "./lib/Types";

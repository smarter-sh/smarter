/**
 * The user menu, as a component, for the web console's other React apps: the single-page console
 * (@smarter/console) renders it in its header, from the console's session (src/lib/userMenu.ts there).
 * main.tsx renders it on the package's development page, from src/mocks/fixtures.ts.
 *
 * The package's source uses relative imports, so that another package's build can import it.
 */
export { default as UserMenu } from "./components/UserMenu";
export type { AppContext, Language, MenuUrls, MenuUser } from "./lib/Types";

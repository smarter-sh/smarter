/**
 * The dashboard, as a component, for the single-page console (@smarter/console), which renders it at /dashboard.
 * main.tsx is the package's development page only.
 *
 * The package's source uses relative imports, so that another package's build can import it.
 */
export { default as Dashboard } from "./components/Dashboard";
export type { AppContextInterface as DashboardContext } from "./Types";

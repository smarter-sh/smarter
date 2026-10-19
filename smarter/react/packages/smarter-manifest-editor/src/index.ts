/**
 * The manifest editor, as a component, for the web console's other React apps: the Prompt Engineer's Workbench
 * (@smarter/workbench) renders it in its Console's Manifest tab. Its own page is main.tsx.
 *
 * The package's source uses relative imports, so that another package's build can import it.
 */
export { default as ManifestEditor } from "./App";
export type { AppProps as ManifestEditorProps } from "./App";

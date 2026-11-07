/**
 * The Prompt Passthrough, as a component, for the single-page console (@smarter/console), which renders it at its page's
 * path. main.tsx is the package's development page only.
 *
 * The package's source uses relative imports, so that another package's build can import it.
 */
export { default as PromptPassthrough } from "./App";
export type { AppProps as PromptPassthroughProps } from "./App";

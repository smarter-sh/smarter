/**
 * Imports mermaid, which lib/mermaid.ts does the first time that a message has a diagram.
 *
 * In the npm package and the web console, the page's bundler splits mermaid into chunks, which are downloaded only
 * then. The embed script, a single classic script, can't be split that way, so its build replaces this module with
 * src/embed/mermaidImport.ts, which imports a separate build of mermaid from beside the script. See vite.config.ts.
 */
export const importMermaid = (): Promise<typeof import("mermaid")> => import("mermaid");

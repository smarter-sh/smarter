/**
 * The embed script's replacement of lib/mermaidImport.ts: it imports the separate build of mermaid, an ES module
 * with its own chunks, from embed/mermaid/ beside embed.js, the first time that a message has a diagram. A classic
 * script can import() a module, so embed.js itself need not be one. See vite.config.ts.
 */
import { assetUrl } from "./assets";

export const importMermaid = (): Promise<typeof import("mermaid")> =>
  import(/* @vite-ignore */ assetUrl("mermaid/mermaid.js"));

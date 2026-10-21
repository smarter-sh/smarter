/**
 * The url of the embed script's own files: the separate build of mermaid, and KaTeX's fonts, in an embed/ directory
 * beside embed.js. They are found from the script's own url, so that embed.js works from a CDN, e.g. jsDelivr, and
 * from a copy on the website itself, e.g. in a WordPress plugin.
 *
 * document.currentScript is the script only while it first runs, so index.ts captures its url then. A script that
 * isn't found, e.g. one that a bundler inlined, uses the files on jsDelivr, of the same version.
 */
import { projectName, projectVersion } from "@/const";

export const CDN_BASE_URL = `https://cdn.jsdelivr.net/npm/${projectName}@${projectVersion}/dist/`;

let baseUrl = CDN_BASE_URL;

/** The url of the directory of a script, or of jsDelivr's copy of the package, if it has no url. */
export function scriptBaseUrl(script: Element | null | undefined): string {
  if (script instanceof HTMLScriptElement && script.src) {
    try {
      return new URL(".", script.src).toString();
    } catch {
      // an unusable src: use the CDN's copy.
    }
  }
  return CDN_BASE_URL;
}

/** Remembers the directory of the running script. Called once, by index.ts, when the script first runs. */
export function captureBaseUrl(script: Element | null | undefined = document.currentScript): string {
  baseUrl = scriptBaseUrl(script);
  return baseUrl;
}

/** The url of one of the embed script's files, e.g. assetUrl("mermaid/mermaid.js"). */
export function assetUrl(path: string): string {
  return new URL(`embed/${path}`, baseUrl).toString();
}

/**
 * The page that frames the editor, if any.
 *
 * Smarter Chat's Console, in the LLMClient prompt workbench, frames the editor of the LLMClient's manifest
 * (smarter.apps.prompt.views.detailviews.prompt_manifest_view.LLMClientManifestEditorView). When the
 * editor saves the manifest, it posts a {@link MANIFEST_SAVED_MESSAGE} message to that page, which then
 * reloads the LLMClient's configuration. The console only allows its own pages to frame it, so that page
 * is of the editor's own origin.
 */
import type { Manifest } from "@/lib/manifest";

/** The type of the message that the editor posts to the page that frames it, when it saves. */
export const MANIFEST_SAVED_MESSAGE = "smarter:manifest-saved";

/** The window of the page that frames the editor, if it is of the editor's own origin, or null. */
export function framingWindow(): Window | null {
  if (window.parent === window) return null;
  try {
    // throws for a page of another origin.
    void window.parent.location.href;
    return window.parent;
  } catch {
    return null;
  }
}

/** Tell the page that frames the editor, if any, that the manifest was saved. */
export function notifySaved(manifest: Manifest) {
  framingWindow()?.postMessage(
    { type: MANIFEST_SAVED_MESSAGE, kind: manifest.kind, name: manifest.metadata.name },
    window.location.origin,
  );
}

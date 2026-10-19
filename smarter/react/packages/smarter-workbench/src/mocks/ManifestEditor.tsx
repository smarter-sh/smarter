/**
 * A test double of @smarter/manifest-editor's ManifestEditor, which needs Monaco, which jsdom can't run: the
 * manifest in a text area, and buttons that save it and delete its resource. The editor's own package tests the
 * real one.
 *
 *     vi.mock("@smarter/manifest-editor", async () => await import("@/mocks/ManifestEditor"));
 */
import type { ManifestEditorProps } from "@smarter/manifest-editor";

export function ManifestEditor({ initialManifest, onSaved, onDeleted, applyApiUrl }: ManifestEditorProps) {
  return (
    <div data-apply-api-url={applyApiUrl}>
      <textarea aria-label="Manifest YAML" defaultValue={initialManifest} />
      <button type="button" onClick={() => onSaved?.({ kind: "LLMClient", name: "stackademy_sql" })}>
        Save
      </button>
      <button type="button" onClick={() => onDeleted?.()}>
        Delete
      </button>
    </div>
  );
}

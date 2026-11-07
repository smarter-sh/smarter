# @smarter/manifest-editor

The manifest editor of the Smarter web console. It renders a resource's manifest as YAML, in a
Monaco editor, and saves, clones and deletes the resource.

The web console's manifest pages render it, e.g. a Guardrail's, `/guardrail/guardrails/<hashed id>/`, and so does
the Prompt Engineer's Workbench, in its Console's Manifest tab.

## Features

- A Monaco YAML editor, with the same options as `@smarter/prompt-passthrough`'s editor, and the
  styling of the console's read-only manifests: rounded corners, a charcoal background and a white
  foreground (`.code-sample-body` in `common-styles.css`).
- A copy button on the editor's top right.
- A toolbar, in the style of `@smarter/prompt-passthrough`'s: save, undo, redo, copy, paste, revert,
  download, clone and delete.
  - Save applies the manifest with the cli api, `/api/v1/cli/apply/`.
  - Clone applies a copy of the manifest, with a new `metadata.name`.
  - Delete deletes the resource with the cli api, `/api/v1/cli/delete/<kind>/?name=<name>`. It is
    disabled while other resources depend on it, as listed in the manifest's `status.dependencies`.

The cli api authenticates the user's Django session, and its brokers enforce the same rules as
the cli, e.g. a delete is refused while other resources depend on the resource.

## Integration

- `src/index.ts` exports the editor as a component, `ManifestEditor`. The single-page console
  (`@smarter/console`) renders it on every manifest page (`src/routes/ManifestPage.tsx`), with the manifest
  that the resource api returns, the cli api's urls, and a session context from the console's session; after
  a delete, it goes back to the resource's list. The package has no build of its own: the console's build
  bundles it, and `index.html` and `src/main.tsx` are a development page.
- The Prompt Engineer's Workbench (`@smarter/workbench`) renders it in its Console's Manifest
  tab, for the LLMClient's manifest: `onSaved` reloads the chat's configuration, and `onDeleted`
  leaves for the LLM Clients list. The package's source uses relative imports, so that another
  package's build can import it, as `@smarter/common`'s does.

## Development

```console
npm run dev     # Vite dev server, with index.html's example manifest
npm run lint
```

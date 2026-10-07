# @smarter/manifest-editor

The manifest editor of the Smarter web console. It renders a resource's manifest as YAML, in a
Monaco editor, and saves, clones and deletes the resource.

It replaces the read-only manifest of `templates/common/manifest_detail.html`, which every
manifest detail page renders, e.g. `smarter.apps.guardrail.views.detailview.GuardrailDetailView`.

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

- `smarter.apps.dashboard.templatetags.react_manifest_editor` provides the app's assets, from its
  Vite `manifest.json`, and the root element's settings: the cli api urls and the cookie names.
- `templates/common/manifest_detail.html` renders the root element, and the manifest, as YAML,
  with Django's `json_script` filter.

## Development

```console
npm run dev     # Vite dev server, with index.html's example manifest
npm run build   # builds into smarter/static/react/@smarter/manifest-editor/
npm run lint
```

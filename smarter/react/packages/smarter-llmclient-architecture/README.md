# @smarter/llmclient-architecture

An LLMClient's architecture: the tree of the SAM resources that it is built from. The Prompt Engineer's
Workbench (`@smarter/workbench`) renders the package's component, `LLMClientArchitecture` (`src/index.ts`), in
its Console's Architecture tab, between Manifest and Server Logs.

The tab opens with a short introduction to SAM resources, their manifests, and how an LLMClient is built from a
tree of them, with links to the documentation. Then each resource is a card, with its kind's icon, its kind, its
name and its owner, joined to the resources that it uses by lines. Clicking a card opens the resource's manifest
page, where its manifest can be edited, in a new tab, and each kind links to its page in the documentation. A
resource that uses others can be collapsed; the toolbar counts the resources, collapses or expands all of them,
and reloads the tree. A resource that the user may not read is a locked card, with its kind and record locator
only.

## Integration

- The tree is `AbstractBroker.dependency_tree()`, a `SAMDependencyTreeNode` (`smarter.lib.manifest.models`),
  which `smarter.apps.prompt.views.detailviews.prompt_architecture_view.LLMClientArchitectureView` returns, and
  the workbench fetches when its tab is first opened. Each node's `url` is the resource's manifest page
  (`smarter.lib.manifest.record_locator.console_url`), and its `icon` a Keen icon (`sam_kind_icon()`).
- `contract/llmclient-architecture.schema.json` is the tree's JSON Schema, which the backend generates
  (`make llmclient-architecture-contract`), and `src/contract.gen.ts` its TypeScript types
  (`npm run contract:types`). `src/contract.test.ts` fails if either is out of date, or if a test fixture
  doesn't match the schema.
- `src/lib/kinds.ts` gives each kind its color, what it does for the LLMClient, and its documentation page.
- The package's source uses relative imports, so that the workbench's build can import it, and
  `@smarter/llmclient-architecture/mocks` exports its fixtures, for the workbench's tests and stories.
- The package has no build of its own: the workbench's build bundles it.
- The text is translated with the web console's `djangojs` catalog.

## Development

```console
npm run dev     # Vite dev server, with the example tree of src/mocks/fixtures.ts
npm run test
npm run lint
```

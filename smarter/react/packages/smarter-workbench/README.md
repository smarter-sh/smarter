# @smarter/workbench

The Prompt Engineer's Workbench of the Smarter web console, at
`/workbench/llm-clients/<hashed_id>/prompt/`: the chat with an LLMClient, and the developer Console beside it.

- **The chat** is `SmarterChat`, from the `@smarter.sh/ui-chat` npm package
  ([smarter-sh/smarter-chat](https://github.com/smarter-sh/smarter-chat), which `make react-install` clones into
  `packages/smarter-chat`). The workbench imports its built library, `dist/`, as any React application does, and
  follows it with its `verbose`, `reloadKey`, `headerActions`, `onConfig`, `onNewChat` and `onModeChange` props.
- **The Console** has six tabs, in the order of a prompt engineer's work: Manifest (the `@smarter/manifest-editor`
  component), Architecture (the `@smarter/llmclient-architecture` component: the tree of the SAM resources that the
  LLMClient is built from), Server Logs (the chat session's server logs, as they stream in, selected when the
  Console opens), Tool Calls and Config (the chat's configuration, as JSON), and Deployment (the
  `@smarter/llmclient-deployment` component). The Manifest, Architecture and Deployment tabs fetch their data when
  they are first opened.
- **The layout**: the separator resizes the chat and the Console, the Console button in the chat's header hides
  the Console, and, in sandbox mode, the Docs button opens a dialog of links to the technical references. The
  browser remembers the layout.

## Integration

- `smarter.apps.prompt.views.detailviews.prompt_workbench_view.PromptWorkbenchView` renders
  `templates/react/workbench.html`, whose root element's attributes are the workbench's configuration
  (`src/lib/session.ts`).
- `smarter.apps.prompt.templatetags.react_workbench` provides the app's assets, from its Vite `manifest.json`.
- `LLMClientManifestEditorView`, `LLMClientArchitectureView` and `LLMClientDeploymentView` return the Manifest,
  Architecture and Deployment tabs' data, as JSON.

## Development

```console
npm run build:deps    # in smarter/react: @smarter/common, and Smarter Chat's library, which the workbench imports
npm run dev           # Vite dev server, with index.html's example LLMClient
npm run build         # builds into smarter/static/react/@smarter/workbench/
npm run test
npm run lint
```

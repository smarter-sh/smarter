# @smarter/workbench

The Prompt Engineer's Workbench of the Smarter web console, at
`/workbench/llm-clients/<hashed_id>/prompt/`: the chat with an LLMClient, and the developer Console beside it.

- **The chat** is `SmarterChat`, from the `@smarter.sh/ui-chat` npm package
  (`packages/smarter.sh-chat` in this workspace). The workbench imports its built library, `dist/`, as any React application does, and
  follows it with its `verbose`, `reloadKey`, `headerActions`, `onConfig`, `onNewChat` and `onModeChange` props.
- **The Console** has six tabs, in the order of a prompt engineer's work: Manifest (the `@smarter/manifest-editor`
  component), Architecture (the `@smarter/llmclient-architecture` component: the tree of the SAM resources that the
  LLMClient is built from), Server Logs (the `@smarter/serverlogs` component: the chat session's server logs, as
  they stream in, selected when the Console opens), Tool Calls and Config (the chat's configuration, as JSON), and Deployment (the
  `@smarter/llmclient-deployment` component). The Manifest, Architecture and Deployment tabs fetch their data when
  they are first opened.
- **The layout**: the separator resizes the chat and the Console, the Console button in the chat's header hides
  the Console, and, in sandbox mode, the Docs button opens a dialog of links to the technical references. The
  browser remembers the layout.

## Integration

- `@smarter/console` imports this package (`src/index.ts`) and renders `Workbench` at
  `/workbench/llm-clients/:id/prompt` (`src/routes/WorkbenchPage.tsx` there), with a `WorkbenchConfig` built from
  the hashed id and the console's session (`src/lib/workbench.ts` there), and the session's onboarding state for
  the tour. The package has no build of its own: its `index.html` and `src/main.tsx` are a development page only.
- Django answers the path with the console's page:
  `smarter.apps.prompt.views.detailviews.prompt_workbench_view.PromptWorkbenchView`, a `ConsoleAppView` (ADR-035)
  that keeps the url name that `LLMClient.workbench_url` reverses.
- `LLMClientManifestEditorView`, `LLMClientArchitectureView` and `LLMClientDeploymentView`, under
  `/api/web/prompt/llm-clients/<hashed_id>/` (`smarter.apps.prompt.api.web.urls`), return the Manifest,
  Architecture and Deployment tabs' data, as JSON.

## Development

```console
npm run build:deps    # in smarter/react: @smarter/common, and Smarter Chat's library, which the workbench imports
npm run dev           # Vite dev server, with index.html's example LLMClient
make react-build      # in the repo's root: builds the console, which imports the workbench
npm run test
npm run lint
```

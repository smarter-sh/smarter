# @smarter/serverlogs

The Smarter web console's server log viewer: the user's server logs, as they stream in. The Prompt Engineer's
Workbench (`@smarter/workbench`) renders the package's component, `ServerLogs` (`src/index.ts`), in its Console's
Server Logs tab, and the Prompt Passthrough (`@smarter/prompt-passthrough`) in its own Server Logs tab.

The records are displayed as the web console's terminal displays them: their text, with its ANSI colors, in the
terminal's palette and font. Long lines scroll horizontally, unless the user wraps them, and the choice is
remembered in the browser, for every viewer. Blocks of pretty-printed JSON are collapsed, each with a toggle, and
the toolbar expands or collapses them all, filters the lines, follows the newest record, copies the lines, and goes
full screen. While the lines have the focus, the viewer has keyboard shortcuts, after k9s, less and vim: `?` lists
them.

## Integration

- `useLogStream(url)` (`src/lib/logStream.ts`) connects to the server log stream,
  `smarter.apps.dashboard.views.terminal_emulator.api.streams.stream_user_logs`, as Server-Sent Events, and returns
  `{ logs, connected, error, clear }`, which are the viewer's props. Its first event is the recent history, and each
  later event is one record.
- The stream's url narrows it: `logStreamUrlForChat()` to one chat session, as the workbench does, and
  `logStreamUrlForRequest()` with `newRequestId()` to one request, as the Prompt Passthrough does, whose request
  sends the id as its `X-Smarter-RequestId` header. `logStreamUrlForLevel()` sets the lowest log level.
- `src/styles.css` is the viewer's stylesheet, which the component imports. The lines' height is
  `--console-server-logs-height`, which the page that renders the viewer may override.
- The package's source uses relative imports, so that the importing packages' builds can import it.
  `@smarter/serverlogs/mocks` exports its fixtures, and `@smarter/serverlogs/fakes` the `EventSource` test double,
  for their tests and stories.
- The package has no build of its own: the importing packages' builds bundle it.
- The text is translated with the web console's `djangojs` catalog.

## Development

```console
npm run dev     # Vite dev server, with the example records of src/mocks/fixtures.ts
npm run test
npm run lint
```

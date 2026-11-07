# Smarter LLM Host Compute List

The LLM Host Compute list of the Smarter web console, at [/llmhost/compute/](http://localhost:9357/llmhost/compute/). The
single-page console, `@smarter/console`, renders this package's `LLMHostComputeList` at that path (see
`smarter-console/src/lib/lists.ts`), with a session context whose api url is the list's. The
package has no build of its own.

- Django page: [smarter.apps.llmhost.views.listview.view.LLMHostComputeListView](../../../smarter/apps/llmhost/views/listview/view.py), a `ConsoleAppView` subclass that keeps the
  page's url name, which the dashboard's global search links to.
- List api: [smarter.apps.llmhost.views.listview.api](../../../smarter/apps/llmhost/views/listview/api.py).

## Development

```console
cd smarter/react
npm run dev -w @smarter/llmhost-compute-list         # http://localhost:5173/, against the Django dev server at :9357
npm run storybook -w @smarter/llmhost-compute-list
npm run test -w @smarter/llmhost-compute-list
```

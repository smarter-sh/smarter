# Smarter Orchestrators List

The Orchestrators list of the Smarter web console, at [/orchestrator/](http://localhost:9357/orchestrator/). The
single-page console, `@smarter/console`, renders this package's `OrchestratorList` at that path (see
`smarter-console/src/lib/lists.ts`), with a session context whose api url is the list's. The
package has no build of its own.

- Django page: [smarter.apps.orchestrator.views.listview.view.OrchestratorListView](../../../smarter/apps/orchestrator/views/listview/view.py), a `ConsoleAppView` subclass that keeps the
  page's url name, which the dashboard's global search links to.
- List api: [smarter.apps.orchestrator.views.listview.api](../../../smarter/apps/orchestrator/views/listview/api.py).

## Screen Shot

![Orchestrator List Screenshot](https://cdn.smarter.sh/github.com/smarter-sh/react/orchestrator-list-screenshot.png)

## Development

```console
cd smarter/react
npm run dev -w @smarter/orchestrator-list         # http://localhost:5173/, against the Django dev server at :9357
npm run storybook -w @smarter/orchestrator-list
npm run test -w @smarter/orchestrator-list
```

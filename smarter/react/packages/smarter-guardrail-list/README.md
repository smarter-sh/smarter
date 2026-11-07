# Smarter Guardrails List

The Guardrails list of the Smarter web console, at [/guardrail/](http://localhost:9357/guardrail/). The
single-page console, `@smarter/console`, renders this package's `GuardrailList` at that path (see
`smarter-console/src/lib/lists.ts`), with a session context whose api url is the list's. The
package has no build of its own.

- Django page: [smarter.apps.guardrail.views.listview.view.GuardrailListView](../../../smarter/apps/guardrail/views/listview/view.py), a `ConsoleAppView` subclass that keeps the
  page's url name, which the dashboard's global search links to.
- List api: [smarter.apps.guardrail.views.listview.api](../../../smarter/apps/guardrail/views/listview/api.py).

## Screen Shot

![Guardrail List Screenshot](https://cdn.smarter.sh/github.com/smarter-sh/react/guardrail-list-screenshot.png)

## Development

```console
cd smarter/react
npm run dev -w @smarter/guardrail-list         # http://localhost:5173/, against the Django dev server at :9357
npm run storybook -w @smarter/guardrail-list
npm run test -w @smarter/guardrail-list
```

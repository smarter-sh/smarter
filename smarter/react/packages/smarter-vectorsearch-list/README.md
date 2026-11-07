# Smarter Vectorsearches List

The Vectorsearches list of the Smarter web console, at [/vectorsearch/](http://localhost:9357/vectorsearch/). The
single-page console, `@smarter/console`, renders this package's `VectorsearchList` at that path (see
`smarter-console/src/lib/lists.ts`), with a session context whose api url is the list's. The
package has no build of its own.

- Django page: [smarter.apps.vectorsearch.views.listview.view.VectorsearchListView](../../../smarter/apps/vectorsearch/views/listview/view.py), a `ConsoleAppView` subclass that keeps the
  page's url name, which the dashboard's global search links to.
- List api: [smarter.apps.vectorsearch.views.listview.api](../../../smarter/apps/vectorsearch/views/listview/api.py).

## Screen Shot

![Vectorsearch List Screenshot](https://cdn.smarter.sh/github.com/smarter-sh/react/vectorsearch-list-screenshot.png)

## Development

```console
cd smarter/react
npm run dev -w @smarter/vectorsearch-list         # http://localhost:5173/, against the Django dev server at :9357
npm run storybook -w @smarter/vectorsearch-list
npm run test -w @smarter/vectorsearch-list
```

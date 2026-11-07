# Smarter Vectorstores List

The Vectorstores list of the Smarter web console, at [/vectorstore/](http://localhost:9357/vectorstore/). The
single-page console, `@smarter/console`, renders this package's `VectorstoreList` at that path (see
`smarter-console/src/lib/lists.ts`), with a session context whose api url is the list's. The
package has no build of its own.

- Django page: [smarter.apps.vectorstore.views.listview.view.VectorstoreListView](../../../smarter/apps/vectorstore/views/listview/view.py), a `ConsoleAppView` subclass that keeps the
  page's url name, which the dashboard's global search links to.
- List api: [smarter.apps.vectorstore.views.listview.api](../../../smarter/apps/vectorstore/views/listview/api.py).

## Screen Shot

![Vectorstore List Screenshot](https://cdn.smarter.sh/github.com/smarter-sh/react/vectorstore-list-screenshot.png)

## Development

```console
cd smarter/react
npm run dev -w @smarter/vectorstore-list         # http://localhost:5173/, against the Django dev server at :9357
npm run storybook -w @smarter/vectorstore-list
npm run test -w @smarter/vectorstore-list
```

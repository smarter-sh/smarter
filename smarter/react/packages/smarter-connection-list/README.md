# Smarter Connections List

The Connections list of the Smarter web console, at [/connection/](http://localhost:9357/connection/). The
single-page console, `@smarter/console`, renders this package's `ConnectionList` at that path (see
`smarter-console/src/lib/lists.ts`), with a session context whose api url is the list's. The
package has no build of its own.

- Django page: [smarter.apps.connection.views.listview.view.ConnectionListView](../../../smarter/apps/connection/views/listview/view.py), a `ConsoleAppView` subclass that keeps the
  page's url name, which the dashboard's global search links to.
- List api: [smarter.apps.connection.views.listview.api](../../../smarter/apps/connection/views/listview/api.py).

## Screen Shot

![Connection List Screenshot](https://cdn.smarter.sh/github.com/smarter-sh/react/connection-list-screenshot.png)

## Development

```console
cd smarter/react
npm run dev -w @smarter/connection-list         # http://localhost:5173/, against the Django dev server at :9357
npm run storybook -w @smarter/connection-list
npm run test -w @smarter/connection-list
```

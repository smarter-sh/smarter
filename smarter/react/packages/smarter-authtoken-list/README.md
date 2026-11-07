# Smarter API Keys List

The API Keys list of the Smarter web console, at [/authtoken/](http://localhost:9357/authtoken/). The
single-page console, `@smarter/console`, renders this package's `AuthTokenList` at that path (see
`smarter-console/src/lib/lists.ts`), with a session context whose api url is the list's. The
package has no build of its own.

- Django page: [smarter.lib.drf.views.listview.view.AuthTokenListView](../../../smarter/lib/drf/views/listview/view.py), a `ConsoleAppView` subclass that keeps the
  page's url name, which the dashboard's global search links to.
- List api: [smarter.lib.drf.views.listview.api](../../../smarter/lib/drf/views/listview/api.py).

## Screen Shot

![AuthToken List Screenshot](https://cdn.smarter.sh/github.com/smarter-sh/react/authtoken-list-screenshot.png)

## Development

```console
cd smarter/react
npm run dev -w @smarter/authtoken-list         # http://localhost:5173/, against the Django dev server at :9357
npm run storybook -w @smarter/authtoken-list
npm run test -w @smarter/authtoken-list
```

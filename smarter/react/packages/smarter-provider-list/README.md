# Smarter Providers List

The Providers list of the Smarter web console, at [/provider/](http://localhost:9357/provider/). The
single-page console, `@smarter/console`, renders this package's `ProviderList` at that path (see
`smarter-console/src/lib/lists.ts`), with a session context whose api url is the list's. The
package has no build of its own.

- Django page: [smarter.apps.provider.views.listview.view.ProviderListView](../../../smarter/apps/provider/views/listview/view.py), a `ConsoleAppView` subclass that keeps the
  page's url name, which the dashboard's global search links to.
- List api: [smarter.apps.provider.views.listview.api](../../../smarter/apps/provider/views/listview/api.py).

## Screen Shot

![Provider List Screenshot](https://cdn.smarter.sh/github.com/smarter-sh/react/provider-list-screenshot.png)

## Development

```console
cd smarter/react
npm run dev -w @smarter/provider-list         # http://localhost:5173/, against the Django dev server at :9357
npm run storybook -w @smarter/provider-list
npm run test -w @smarter/provider-list
```

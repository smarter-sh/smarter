# Smarter Proxies List

The Proxies list of the Smarter web console, at [/proxy/](http://localhost:9357/proxy/). The
single-page console, `@smarter/console`, renders this package's `ProxyList` at that path (see
`smarter-console/src/lib/lists.ts`), with a session context whose api url is the list's. The
package has no build of its own.

- Django page: [smarter.apps.proxy.views.listview.view.ProxyListView](../../../smarter/apps/proxy/views/listview/view.py), a `ConsoleAppView` subclass that keeps the
  page's url name, which the dashboard's global search links to.
- List api: [smarter.apps.proxy.views.listview.api](../../../smarter/apps/proxy/views/listview/api.py).

## Screen Shot

![Proxy List Screenshot](https://cdn.smarter.sh/github.com/smarter-sh/react/proxy-list-screenshot.png)

## Development

```console
cd smarter/react
npm run dev -w @smarter/proxy-list         # http://localhost:5173/, against the Django dev server at :9357
npm run storybook -w @smarter/proxy-list
npm run test -w @smarter/proxy-list
```

# Smarter MCP Clients List

The MCP Clients list of the Smarter web console, at [/mcpclient/](http://localhost:9357/mcpclient/). The
single-page console, `@smarter/console`, renders this package's `MCPClientList` at that path (see
`smarter-console/src/lib/lists.ts`), with a session context whose api url is the list's. The
package has no build of its own.

- Django page: [smarter.apps.mcpclient.views.listview.view.MCPClientListView](../../../smarter/apps/mcpclient/views/listview/view.py), a `ConsoleAppView` subclass that keeps the
  page's url name, which the dashboard's global search links to.
- List api: [smarter.apps.mcpclient.views.listview.api](../../../smarter/apps/mcpclient/views/listview/api.py).

## Screen Shot

![MCPClient List Screenshot](https://cdn.smarter.sh/github.com/smarter-sh/react/mcpclient-list-screenshot.png)

## Development

```console
cd smarter/react
npm run dev -w @smarter/mcpclient-list         # http://localhost:5173/, against the Django dev server at :9357
npm run storybook -w @smarter/mcpclient-list
npm run test -w @smarter/mcpclient-list
```

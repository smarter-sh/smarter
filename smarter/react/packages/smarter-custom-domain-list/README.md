# Smarter Custom Domains List

The Custom Domains list of the Smarter web console, at [/llmclient/custom-domains/](http://localhost:9357/llmclient/custom-domains/). The
single-page console, `@smarter/console`, renders this package's `CustomDomainList` at that path (see
`smarter-console/src/lib/lists.ts`), with a session context whose api url is the list's. The
package has no build of its own.

- Django page: [smarter.apps.llmclient.views.listview.view.CustomDomainListView](../../../smarter/apps/llmclient/views/listview/view.py), a `ConsoleAppView` subclass that keeps the
  page's url name, which the dashboard's global search links to.
- List api: [smarter.apps.llmclient.views.listview.api](../../../smarter/apps/llmclient/views/listview/api.py).

## Screen Shot

![Custom Domain List Screenshot](https://cdn.smarter.sh/github.com/smarter-sh/react/custom-domain-list-screenshot.png)

## Development

```console
cd smarter/react
npm run dev -w @smarter/custom-domain-list         # http://localhost:5173/, against the Django dev server at :9357
npm run storybook -w @smarter/custom-domain-list
npm run test -w @smarter/custom-domain-list
```

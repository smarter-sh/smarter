# Smarter LLMClients List

The LLMClients list of the Smarter web console, at [/workbench/](http://localhost:9357/workbench/). The
single-page console, `@smarter/console`, renders this package's `LLMClientList` at that path (see
`smarter-console/src/lib/lists.ts`), with a session context whose api url is the list's. The
package has no build of its own.

- Django page: [smarter.apps.prompt.views.listview.view.PromptListView](../../../smarter/apps/prompt/views/listview/view.py), a `ConsoleAppView` subclass that keeps the
  page's url name, which the dashboard's global search links to.
- List api: [smarter.apps.prompt.views.listview.api](../../../smarter/apps/prompt/views/listview/api.py).

## Screen Shot

![LLMClient List Screenshot](https://cdn.smarter.sh/github.com/smarter-sh/react/prompt-list-screenshot.png)

## Development

```console
cd smarter/react
npm run dev -w @smarter/llmclient-list         # http://localhost:5173/, against the Django dev server at :9357
npm run storybook -w @smarter/llmclient-list
npm run test -w @smarter/llmclient-list
```

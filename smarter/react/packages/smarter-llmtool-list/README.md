# Smarter LLM Tools List

The LLM Tools list of the Smarter web console, at [/llm-tools/](http://localhost:9357/llm-tools/). The
single-page console, `@smarter/console`, renders this package's `LLMToolList` at that path (see
`smarter-console/src/lib/lists.ts`), with a session context whose api url is the list's. The
package has no build of its own.

- Django page: [smarter.apps.llmtool.views.listview.view.PluginListView](../../../smarter/apps/llmtool/views/listview/view.py), a `ConsoleAppView` subclass that keeps the
  page's url name, which the dashboard's global search links to.
- List api: [smarter.apps.llmtool.views.listview.api](../../../smarter/apps/llmtool/views/listview/api.py).

## Screen Shot

![LLMTool List Screenshot](https://cdn.smarter.sh/github.com/smarter-sh/react/plugin-list-screenshot.png)

## Development

```console
cd smarter/react
npm run dev -w @smarter/llmtool-list         # http://localhost:5173/, against the Django dev server at :9357
npm run storybook -w @smarter/llmtool-list
npm run test -w @smarter/llmtool-list
```

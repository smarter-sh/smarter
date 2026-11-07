# Canonical Django + React Reference

The Guardrail list page is the reference. Read these files together. Each one
names the others' identifiers, so read them as a set. Paths that start with
`packages/` are in smarter-sh/smarter-console (a checkout at `../smarter-console`).

| Layer                                                   | File                                                                                                                                                                          |
| ------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Sidebar URL                                             | `smarter/smarter/apps/dashboard/context_processors.py` (`"guardrails": reverse(...)`), sent as `ConsoleSidebar.guardrails` by `smarter/smarter/apps/api/web/session/views.py` |
| Sidebar item                                            | `packages/smarter-console/src/lib/sidebar.ts` (`key: "guardrails"`)                                                                                                           |
| Console route                                           | `packages/smarter-console/src/lib/lists.ts` (`LIST_PAGES`), `src/router.tsx` (`listRoute`) and `src/routes/ListPage.tsx`                                                      |
| URL names and routes                                    | `smarter/smarter/apps/guardrail/urls.py` (`GuardrailReverseNames`)                                                                                                            |
| Page view                                               | `smarter/smarter/apps/guardrail/views/listview/view.py` (`GuardrailListView(ConsoleAppView)`)                                                                                 |
| List, clone, rename, delete api                         | `smarter/smarter/apps/guardrail/views/listview/api.py`                                                                                                                        |
| Serializer (`can_delete`, `manifest_url`, `detail_url`) | `smarter/smarter/apps/guardrail/serializers.py` and its base, `MetaDataWithOwnershipModelSerializer` in `smarter/smarter/apps/account/serializers.py`                         |
| React export                                            | `packages/smarter-guardrail-list/src/index.ts` (`GuardrailList`)                                                                                                              |
| React app                                               | `packages/smarter-guardrail-list/src/App.tsx` and `src/components/`                                                                                                           |
| Development page                                        | `packages/smarter-guardrail-list/src/main.tsx` and `vite.config.ts`                                                                                                           |
| Shared React code                                       | `packages/smarter-common/src/lib/{django,load,actionUrl,Types}.tsx` and `src/components/TabbedListView`                                                                       |
| Python tests                                            | `smarter/smarter/apps/guardrail/tests/test_views.py` (`ResourceViewsTestMixin`)                                                                                               |
| Console tests                                           | `packages/smarter-console/src/routes/ListPage.test.tsx`                                                                                                                       |

The one page that Django still renders with a React app, a deployed LLMClient's host's page, has a template tag
(`smarter/smarter/apps/llmclient/templatetags/react_llmclient_deployment.py`, through the manager in
`smarter/smarter/lib/django/templatetags/smarter_react_templatetag_manager.py`), a template
(`smarter/smarter/templates/llmclient/endpoints.html`) and a `main.tsx` that reads the root element's
attributes (`packages/smarter-llmclient-deployment/src/main.tsx`). Every console page had the same, until it
moved into the console: the list pages until release v0.42.10.

## The names that must agree

For a kind `widget`:

| Name                       | Where it appears                                                                                                         |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `@smarter/widget-list`     | `package.json` `name`, the console's `package.json` dependency, and `LIST_PAGES`' `load`                                 |
| `WidgetList`               | the export of `src/index.ts`, and `LIST_PAGES`' `load`                                                                   |
| `/widget`                  | the console's route (`LIST_PAGES`' `path`), the Django page's path without its slash, and the sidebar's item             |
| `WidgetListView`           | the Django page's class, a `ConsoleAppView` subclass, named after `WidgetListApiView`, which `listview_registry()` pairs |
| `smarter-widget-list-root` | the development page's `index.html` and `main.tsx`                                                                       |

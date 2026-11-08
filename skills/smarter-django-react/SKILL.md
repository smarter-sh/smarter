---
name: smarter-django-react
description: Use when changing the backend side of a Smarter web console page - the Django view that serves a console path (ConsoleAppView and its one-line subclasses that keep a page's url name), a resource list's api (SmarterListApiView, list/clone/rename/delete under /api/web/), a manifest page's view and kind, the session api (GET /api/web/session/, ConsoleSession, the sidebar), the docs pages' views, the one page Django still renders with a React app (a deployed LLMClient's host, its template tag and Vite manifest), installing the console's build (make console, smarter-console-version.txt), static files on the CDN, or a console page that answers 503 or renders blank. The React code itself is in smarter-sh/smarter-console: load its smarter-console-development skill for that side.
---

# Smarter Django + React: the backend side

The web console is a single-page app, `@smarter/console`
([ADR-035](../../docs/source/adr/035-single-page-app.rst)), whose source is its own repository,
[smarter-sh/smarter-console](https://github.com/smarter-sh/smarter-console) (a checkout usually sits next
to this one, at `../smarter-console`). Every console page (sign-in, the frame, the dashboard, the resource
lists, the manifest pages, the workbench, the Extensions console, the tool pages, the docs pages) is a
route of the console, which meets this repository only over HTTP and through its build:

- Django answers each console path with the console's `index.html` (a `ConsoleAppView` that keeps the
  page's url name). Never add a page as a Django template.
- The console reads the session (`GET /api/web/session/`), the web console api (`/api/web/<app>/`) and
  the public api (`/api/v1/`). A change to what the console shows is usually a change to one of those
  and its contract.
- This repository installs a pinned console release: `smarter-console-version.txt`, and `make console`
  (`scripts/fetch_console.py`) unpacks its `react/@smarter/<package>/` into `smarter/smarter/static/react/`
  and its `i18n/messages.js` into `smarter/console/i18n/` (see `smarter-translations`).

For the React side (routes in `lib/lists.ts` and `lib/manifestPages.ts`, `lib/sidebar.ts`, list packages,
`@smarter/common`'s `fetchDjangoUrl` and `TabbedListView`, stories and tests), load smarter-console's
`smarter-console-development` skill, in `../smarter-console/skills/`. A feature that needs both is two
changes: the backend here first, then the console, which copies the backend's contracts with its
`make contracts`.

## How a list page is wired, end to end

```
sidebar link (the session's sidebar, GET /api/web/session/, from sidebar_context())
  → the console's route for the list (smarter-console: lib/lists.ts LIST_PAGES)
    → the list POSTs to the list API with fetchDjangoUrl (CSRF + X-Smarter-* headers)
      → views/listview/api.py returns {"objects": [...]} serialized with can_delete, manifest_url, detail_url
Django answers the list's own path, e.g. /guardrail/, with the console's index.html: <Kind>ListView(ConsoleAppView)
```

## A list page

1. **Page view** (`<app>/views/listview/view.py`): a one-line subclass of
   `ConsoleAppView` (`smarter.apps.dashboard.views.console_app`), named after its list api,
   `<Kind>ListView` for `<Kind>ListApiView`, routed at the list's path with its url name.
   `listview_registry()` pairs them by that name, and the dashboard's global search links
   to the page through it. Copy `apps/guardrail/views/listview/view.py`. It has no template
   and no template tag.
2. **The list API**, below, and the **sidebar** link.
3. **Tests**: the app's `ResourceViewsTestMixin` class checks that the page is a `ConsoleAppView`.
4. **The console**: a `LIST_PAGES` entry and a list package, in smarter-console.

## A manifest page

A resource's manifest page, e.g. `/guardrail/guardrails/<hashed id>/`, is the console's too. For a new kind:

1. **Page view** (`<app>/views/detailview.py`): a one-line `ConsoleAppView` subclass, routed at
   the page's path with its url name, which `console_paths()` in
   `smarter/smarter/lib/manifest/record_locator.py` reverses: add the model there.
2. **Kind**: add the model's record locator prefix and its SAM kind to
   `KIND_BY_RECORD_LOCATOR_PREFIX` in `apps/dashboard/resource_detail.py`, unless the model has its
   own `kind` field, as a plugin does. `test_kinds_of_the_manifest_pages` checks it.
3. **The console** reads `/api/web/dashboard/resource/<prefix>-<id>/` (a `MANIFEST_PAGES` entry in
   smarter-console).

## A console page that shows one resource

The workbench (`/workbench/llm-clients/<hashed_id>/prompt/`) is the example. Its view,
`PromptWorkbenchView`, is a `ConsoleAppView` subclass that keeps its url name. The console asks the
resource api, `/api/web/dashboard/resource/<prefix>-<id>/`, first, and shows Page not found on its 404,
which is also the answer for a resource the user may not read. The page's own JSON endpoints are in
`/api/web/<app>/`, and refuse a resource the user may not read with the same 404.

## A public page: the docs

The docs pages (`/docs/...`) are console routes that a visitor reads without signing in, so their data
must be public too: the session's `samKinds`, the cli api's `example-manifest` and `json-schema`
commands, and `/api/v1/openapi.json`. Django serves the console at each path with a `ConsoleAppView`
subclass (`smarter.apps.docs.views`); a path with an argument, such as a kind, checks it and answers 404
for one that doesn't exist.

## A page that Django renders: a deployed LLMClient's host

A deployed LLMClient's own host serves only that LLMClient, so its page at `/` is outside the console, and Django
renders it with the template-tag pattern:

1. **Template tag** (`apps/llmclient/templatetags/react_llmclient_deployment.py`):
   `SmarterReactTemplateTagManager(app_name="@smarter/llmclient-deployment", templatetag_name=__name__)`.
   It reads `smarter/smarter/static/react/@smarter/llmclient-deployment/manifest.json` (installed by
   `make console`, validated against `ViteManifest`), and a `@register.simple_tag` returns
   `templatetag_manager.reactapp_build_assets`: the hashed CSS and JS file names.
2. **Template** (`templates/llmclient/endpoints.html`): emits the CSS and the JS, the page's data with
   `json_script`, and the root `<div>`.
3. **Data**: `deployment_page()` builds `LLMClientDeploymentPage`
   (`apps/llmclient/views/deployment_contract.py`), whose JSON Schema
   `make llmclient-deployment-contract` regenerates.

Don't add another: a new page is a console page.

## The list API

1. **List API** (`<app>/views/listview/api.py`), routed in the **web console
   api**, `<app>/api/web/urls.py`, at `/api/web/<app label>/`, never in the
   app's console `urls.py` ([ADR-034](../../docs/source/adr/034-web-console-api.rst)).
   The module has an `<App>ApiWebReverseNames` class whose `namespace` is
   `f"{path_namespace}:{namespace}"` (`api:web:<app>`, `path_namespace` from
   `smarter.apps.api.web.const`), and `smarter/smarter/apps/api/web/urls.py`
   includes it, with the path `f"{<app>_namespace}/"`. Copy
   `apps/guardrail/api/web/urls.py`, including its module docstring's paragraph
   that names the module as part of the Django-React integration and links
   `:doc:`/smarter-framework/developer-reference/react-integration``.
   - `listview/(owned|shared|all)/`: a subclass of
     `SmarterListApiView` (`smarter.lib.django.listview`) that sets `model`,
     `serializer_class`, `listview_cache_kind`, `sort_fields`, and the
     `select_related`/`prefetch_related` its serializer reads. Never write its
     `post()`: the base class filters by ownership, paginates, filters by
     `?tag=` and `?annotation=`, and caches each page per user in Redis.
     `?invalidate_cache=true` (the Refresh button) rebuilds the user's pages.
   - In the app's `receivers.py`, `connect_listview_cache("<Kind>", "<app>.<Model>", ...)`
     with every model the list shows (nested rows, names of related resources,
     rows that decide `can_delete`), or its cached pages go stale. After a
     `QuerySet.update()` of a shown column, call `invalidate_listview_cache("<Kind>")`.
   - A serializer method that reads a reverse relation uses
     `related_rows(obj, "<accessor>", <RowModel>, ...)` from
     `smarter.lib.django.serializers`, so the prefetch is used. Check the page's
     query count with `CaptureQueriesContext`: it should not grow per row.
   - `clone/<id>/<new_name>/`, `rename/<id>/<new_name>/`, and `delete/<id>/`,
     siblings of `listview/` (the console's `actionUrl()` relies on it).
   - The list page's view class is named after its api's (`GuardrailListView`
     for `GuardrailListApiView`): `listview_registry()` pairs them by name, and
     the dashboard's global search (`smarter.apps.dashboard.search`) finds every
     list api through it, so keep that naming, or
     `test_every_list_api_has_its_page` fails. Set `listview_label` when the
     model's plural verbose name is a poor label.
   - The serializer sends `can_delete` (the console disables Delete when it is
     false, and shows the server's error when a delete fails) and, through
     `MetaDataWithOwnershipModelSerializer`, `manifest_url` and `detail_url`,
     from which the console's detail dialog reads the manifest and the
     resource's hierarchy. Every field arrives camel-cased (`canDelete`).
   - Any other JSON endpoint the console calls (a dashboard widget, a
     dialog's data) goes under `/api/web/<app label>/` too. Only pages stay
     outside `/api/`.
   - All are POSTs, scoped to what the user may read, own, or delete. A
     superuser sees every account's rows.
2. **Sidebar**: add the URL to `sidebar_context()` in
   `smarter/smarter/apps/dashboard/context_processors.py` and a field to `ConsoleSidebar`
   (`smarter.apps.api.web.session`), then `make console-session-contract`. The console's
   `lib/sidebar.ts` gets the item. Never leave the sidebar pointing at a placeholder.
3. **Headers**: the console sends `X-CSRFToken` and `X-Smarter-Client`, `-ClientVersion`,
   `-ClientType`, `-RequestId` and `-Capabilities`. A new custom header must also be added to
   `CORS_ALLOW_HEADERS` in `smarter/smarter/settings/base.py`.

See [references/canonical-django-react-reference.md](references/canonical-django-react-reference.md)
for the files to read.

## Contracts the console reads

The backend owns them; each is a Pydantic model with a committed JSON Schema, regenerated and committed
here by its make target. smarter-console's `make contracts` copies them into its packages and regenerates
their TypeScript, and smarter-sh/automation's weekly API Contract Sync proposes that copy.

| Contract                    | Schema, under `smarter/smarter/apps/`                         | Target                                 |
| --------------------------- | ------------------------------------------------------------- | -------------------------------------- |
| The session                 | `api/web/session/console-session.schema.json`                 | `make console-session-contract`        |
| Smarter Chat's api          | `prompt/contract/chat-contract.schema.json`                   | `make chat-contract`                   |
| The Extensions console      | `llmtool/extension/extension-console.schema.json`             | `make extension-contract`              |
| The LLM tool list           | `llmtool/views/listview/extension-list.schema.json`           | `make llmtool-list-contract`           |
| A deployed LLMClient's page | `llmclient/views/llmclient-deployment.schema.json`            | `make llmclient-deployment-contract`   |
| The Architecture tab        | `prompt/views/detailviews/llmclient-architecture.schema.json` | `make llmclient-architecture-contract` |

Add a field as optional unless every console release in use sends or reads it: the console that a
deployment runs is the pinned release, not the newest.

## A console page answers 503, or renders blank

- **503 "The web console hasn't been built"**: `ConsoleAppView` found no
  `STATIC_ROOT/react/@smarter/console/index.html`. Run `make console` (the pinned release), or
  `make console-local CONSOLE_DIST=../smarter-console/dist` (a local build of smarter-console, after
  its `make build`), then `make collectstatic`, then `make build && make run` (`make run` in the
  background). `make build` builds the image with `DOCKER_COLLECT_STATIC_FILES=false`, so it uses the
  host's previously collected `smarter/staticfiles/`.
- **A deployed LLMClient's page renders an empty root, with no console errors**: the template tag
  found no `manifest.json`. Check `staticfiles/react/@smarter/llmclient-deployment/manifest.json` in
  `smarter-api`. The template tag caches a missing manifest for the life of the process, so restart
  `smarter-api` after fixing the static files.

These commands are safe to run without asking: their output (`smarter/staticfiles/`,
`smarter/smarter/static/react/`, the image) isn't tracked by git, and they touch no infrastructure.

## Static files on the CDN

With `SMARTER_STATIC_FILES_ON_CDN` on (AWS only, off locally), `STATIC_URL` is `cdn.<platform>/static/`,
and `ConsoleAppView` rewrites the console page's `/static/` urls to it once `initialize_platform` has
uploaded that build (`smarter.lib.django.static_storage`, `mark_console_uploaded()`). Until then the
pods serve it. So the console's scripts never hard-code `/static/` (smarter-console's rule). Never
upload to the bucket from a test: `initialize_platform`'s `collectstatic` is patched in its tests.

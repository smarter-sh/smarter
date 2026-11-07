---
name: smarter-django-react
description: Use when building or changing a React app of the Smarter web console, especially a resource list page (smarter-<kind>-list), which the single-page console (@smarter/console) renders, or one of the pages that Django still hosts (workbench, Prompt Passthrough, Terminal, manifest drop zone). The Extensions console is the console's too. Covers the console's list routes (lib/lists), the Django page class that keeps a list's url name, the Django view, template and templatetag of a hosted page, SessionContext and fetchDjangoUrl in @smarter/common, the list/clone/rename/delete API contract, importable packages, and the sidebar link.
---

# Smarter Django + React

The web console is moving into a single-page app, `@smarter/console`
([ADR-035](../../docs/source/adr/035-single-page-app.rst), `docs/spa-migration.md`). Its sign-in pages,
frame (sidebar, header, user menu, welcome dialog), dashboard, every resource list and the Extensions console
(`routes/ExtensionsPage`) and every resource's manifest page but the LLMClient's are the console's: it renders
each package's component at the page's path. The other
pages are still Django pages that each embed one React app, built by Vite into Django's static files: the
workbench, the Prompt Passthrough, the Terminal and the manifest drop zone. The apps live in the npm workspace
`smarter/react/packages/`, and share code through `@smarter/common`.

## How a list page is wired, end to end

```
sidebar link (the session's sidebar, GET /api/web/session/, from sidebar_context())
  → the console's route for the list (lib/lists.ts LIST_PAGES), which loads @smarter/<kind>-list lazily
    → ListPage builds a SessionContext from the session, whose ApiUrl is the list api, and renders <List>
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
2. **Console route**: an entry in `smarter-console/src/lib/lists.ts` (`LIST_PAGES`): the
   path without its trailing slash, the list api, the package's export, and `visible` when
   the backend limits the page (a feature flag, superusers only). The router and the
   sidebar take it from there. Add the package to the console's `package.json`.
3. **Tests**: the app's `ResourceViewsTestMixin` class checks that the page is a
   `ConsoleAppView`, and the console's `routes/ListPage.test.tsx` checks every entry.

## A manifest page

A resource's manifest page, e.g. `/guardrail/guardrails/<hashed id>/`, is the console's too. For a new kind:

1. **Page view** (`<app>/views/detailview.py`): a one-line `ConsoleAppView` subclass, routed at
   the page's path with its url name, which `console_paths()` in
   `smarter/smarter/lib/manifest/record_locator.py` reverses: add the model there.
2. **Kind**: add the model's record locator prefix and its SAM kind to
   `KIND_BY_RECORD_LOCATOR_PREFIX` in `apps/dashboard/resource_detail.py`, unless the model has its
   own `kind` field, as a plugin does. `test_kinds_of_the_manifest_pages` checks it.
3. **Console route**: an entry in `smarter-console/src/lib/manifestPages.ts` (`MANIFEST_PAGES`):
   the path with `:id`, the record locator prefix, the list to go back to after a delete, and
   `visible` as for its list. `routes/ManifestPage.tsx` reads
   `/api/web/dashboard/resource/<prefix>-<id>/` and renders `@smarter/manifest-editor`.

## A page that Django still hosts

1. **View**: a `SmarterAuthenticatedNeverCachedWebView` that renders
   `react/<page>.html` with one context key containing:
   - `root_id`: `"smarter-<page>-root"`
   - `django_csrf_cookie_name`, `django_session_cookie_name`, and
     `cookie_domain`, from `settings`
   - its api urls, e.g. `reverse(<App>ApiWebReverseNames.namespace, <App>ApiWebReverseNames.<name>)`
   - `react_debug_mode`: the `ENABLE_REACTAPP_DEBUG_MODE` waffle switch
   - `smarter_request_id`: `self.generate_smarter_request_id()`
2. **Template tag** (`<app>/templatetags/react_<page>.py`):
   `SmarterReactTemplateTagManager(app_name="@smarter/<page>", templatetag_name=__name__)`.
   It reads `smarter/smarter/static/react/@smarter/<page>/manifest.json`.
   The module defines a `@register.simple_tag` named `<page>_react_assets`
   that returns `templatetag_manager.reactapp_build_assets`: the hashed CSS and
   JS file names. See `apps/prompt/templatetags/react_workbench.py`.
3. **Template** (`smarter/smarter/templates/react/<page>.html`): extends
   `dashboard/base.html`, emits the CSS in `style_extra` and the JS in
   `javascript_extra`, and renders the root `<div>`, with each context value as
   an attribute.

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
     `post()`: the base class filters by ownership, paginates, and caches each
     page per user in Redis. `?invalidate_cache=true` (the Refresh button)
     rebuilds the user's pages.
   - In the app's `receivers.py`, `connect_listview_cache("<Kind>", "<app>.<Model>", ...)`
     with every model the list shows (nested rows, names of related resources,
     rows that decide `can_delete`), or its cached pages go stale. After a
     `QuerySet.update()` of a shown column, call `invalidate_listview_cache("<Kind>")`.
   - A serializer method that reads a reverse relation uses
     `related_rows(obj, "<accessor>", <RowModel>, ...)` from
     `smarter.lib.django.serializers`, so the prefetch is used. Check the page's
     query count with `CaptureQueriesContext`: it should not grow per row.
   - `clone/<id>/<new_name>/`, `rename/<id>/<new_name>/`, and `delete/<id>/`,
     siblings of `listview/` (React's `actionUrl()` relies on it).
   - The list page's view class is named after its api's (`GuardrailListView`
     for `GuardrailListApiView`): `listview_registry()` pairs them by name.
   - Any other JSON endpoint a React app calls (a dashboard widget, a
     dialog's data) goes under `/api/web/<app label>/` too. Only pages stay
     outside `/api/`.
   - All are POSTs, scoped to what the user may read, own, or delete. A
     superuser sees every account's rows.
2. **Sidebar**: add the URL to `sidebar_context()` in
   `smarter/smarter/apps/dashboard/context_processors.py`, the link to
   `smarter/smarter/templates/dashboard/sidebar.html` (the sidebar of the pages that Django
   still hosts), a field to `ConsoleSidebar` (`smarter.apps.api.web.session`) and the item to
   the console's `lib/sidebar.ts`. Never leave the sidebar pointing at a placeholder.

## The React side

- **A list package is import-only**: its `src/index.ts` exports `<Kind>List`, its `App`,
  which takes `sessionContext` (and may take `onboarding`). Its `main.tsx` is a development
  page that renders it from `src/mocks/fixtures.ts`, and it has no build. A page that Django
  still hosts has a `main.tsx` that reads its root element's attributes, throws if a
  required one is missing, builds a `SessionContext`, and renders `<App>`.
- **`fetchDjangoUrl(sessionContext, url, requestJson)`**
  (`@smarter/common`, `lib/django.tsx`) POSTs with the `X-CSRFToken` header,
  read from the CSRF cookie, plus `X-Smarter-Client`,
  `X-Smarter-ClientVersion`, `X-Smarter-ClientType`, `X-Smarter-RequestId`, and
  `X-Smarter-Capabilities`. A new custom header must also be added to Django's
  `CORS_ALLOW_HEADERS` in `smarter/smarter/settings/base.py`.
- **`load()`** (`lib/load.tsx`) fetches `<ApiUrl>/<owned|shared|all>/?invalidate_cache=...`
  and reads `objects`. `TabbedListView` shows each page from `lib/cache.tsx`
  (localStorage, keyed by `sessionScope()`, the tab, page, ordering and filter;
  never searches) at once, with a "Refreshing" spinner, while it loads.
- **`actionUrl(sessionContext, "clone/12/new_name/")`** turns the list URL into
  its sibling action URL.
- **`TabbedListView`** (`@smarter/common`) gives the owned/shared tabs. A list
  is a `ListView` (table) and a `DetailView`, with a `Toolbar` and a
  `StatusBar`. There is no card view.
- **Choosing a row opens its detail.** `TabbedListView` listens for clicks and
  Enter on the ListView's rows, and opens `ResourceDetail`, a dialog whose tabs
  are the list's `DetailView` (one object), the resource's manifest, the
  hierarchy of what it uses, and what uses it. The last three come from the
  row's `detailUrl`, which `MetaDataWithOwnershipModelSerializer` adds
  (`smarter.apps.dashboard.resource_detail`); a row without one, e.g. an
  Extension's, has the Details tab only. The rules for a ListView: exactly one
  `<tr>` per object, directly in `<tbody>`, loading rows with class `ghost`
  (the row's index among `tbody > tr:not(.ghost)` is its object's), and the Name
  cell is plain text, not a link. Clicks on a row's links, buttons and chips do
  what they do instead.
- **A `DetailView`** is built from `DetailOverview` (description, status,
  Toolbar), `DetailSection`s of `DetailField`s (typed: `text`, `code`, `url`,
  `dateTime`, `number`, `bool`, `json`, `list`), and `ResourceMetadataSection`
  (owner, account, version, ids, dates, tags, annotations), all from
  `@smarter/common`. Never copy a `renderDetail` helper into a package.
  See `smarter-guardrail-list/src/components/DetailView/`.
- **Tags and annotations**: a `DetailView` gets them from
  `ResourceMetadataSection`, and a ListView may render `TagChips` and
  `AnnotationChips`, passing the `filtering` prop that `TabbedListView` gives
  it, so that clicking a chip narrows the list. Its props interface declares
  `filtering?: Filtering`. `TabbedListView` sends `?tag=` and
  `?annotation=` (each repeatable), and `SmarterListApiView` applies them, so a
  new list api needs nothing for them. A new list api is also searched by the
  dashboard's global search (`smarter.apps.dashboard.search`), through
  `listview_registry()`, which pairs it with the `<Kind>ListView` page of the same
  urlconf: keep that naming, or `test_every_list_api_has_its_page` fails. Set
  `listview_label` when the model's plural verbose name is a poor label.
- The list API's serializer sends `can_delete`, which arrives camel-cased as
  `canDelete`. The Toolbar disables its Delete button when `canDelete === false`,
  with a title that explains why (see
  `smarter-guardrail-list/src/components/Toolbar/Component.tsx`). The server
  still enforces deletion, so show its error message when a delete fails.
  Budgets aren't owned resources: their list shows Delete only when the API
  reports `isSuperuser`.
- The API camel-cases every field (`manifest_url` → `manifestUrl`). Search the
  React code for the camelCase name.

## Creating a new list package

Copy the closest existing list package, then rename it everywhere.
`smarter-guardrail-list` is the reference.

1. `cp -R smarter/react/packages/smarter-guardrail-list smarter/react/packages/smarter-<kind>-list`
   (without `node_modules`, `dist`, `CHANGELOG.md`, or `.DS_Store`).
2. Rename it in `package.json` (`name` and `description`; keep `"private": true`, `main`
   and `exports`), `index.html`, `main.tsx` (the root id), `src/index.ts` (the export's
   name), `lib/const.tsx`, and `README.md`.
3. Replace the `Types.tsx` object type, and the table columns and the
   DetailView's sections, with the new serializer's fields.
4. Update the stories, the MSW fixtures and handlers, and the tests. See
   `smarter-react-testing`.
5. Add it to the console (step 2 of "A list page"), `make react-install`, then
   `make react-build`, which builds the console with it.

See [references/canonical-django-react-reference.md](references/canonical-django-react-reference.md)
for the files to read.

## One package that imports another

A console app can render another package's component. For example, the Prompt Engineer's Workbench
(`smarter-workbench`) renders the manifest editor, the LLMClient architecture and the LLMClient deployment
page in its Console's tabs, and imports Smarter Chat. The workbench and the Prompt Passthrough both render the
server log viewer, `smarter-serverlogs`, in their Server Logs tabs: one package, rather than a copy in each. A package that exists only to be imported, such as
`smarter-llmclient-architecture`, has no `build` script: `npm run dev` renders its fixtures, and the importing
package's build bundles it. The workspace's shared configuration maps `@/` to the _importing_
package's `src/`, so a package whose source another package imports follows these rules:

- **Its source uses relative imports**, not `@/`, as `@smarter/common`'s does. Its tests, stories and
  mocks may keep `@/`, because they run only in their own package. `smarter-manifest-editor`,
  `smarter-llmclient-architecture`, `smarter-llmclient-deployment` and `smarter-serverlogs` do this.
- **Its `package.json` exports its source**: `"main"` and `"exports": {".": "./src/index.ts"}`.
  `src/index.ts` exports the component and its props type. Fixtures that other packages' tests
  use are exported as a subpath, e.g. `"./mocks"` in `smarter-llmclient-deployment`.
- **A component that was a page takes callbacks** in place of whatever it did to its page or a
  framing page, e.g. the manifest editor's `onSaved` and `onDeleted`.
- **Smarter Chat is the exception.** It is a published npm library (`@smarter.sh/ui-chat`), with
  `@/` imports, so the workbench imports its built library (`packages/smarter.sh-chat/dist/`), as
  npm users do. `npm run build:deps` builds it and `@smarter/common`; `make react-test`,
  `make react-lint` and CI run it first.

Don't frame a console page in an iframe to reuse it: export its component instead.

## A blank page with no console errors

A page that Django still hosts renders an empty root element, and the browser console shows nothing:
the app's build is missing from the static files. `make build` builds the image
with `DOCKER_COLLECT_STATIC_FILES=false`, so it uses the host's previously
collected `smarter/staticfiles/`, in which a new or rebuilt app is missing. The
template tag then finds no `manifest.json` and emits no script tags.

- Check `staticfiles/react/<app>/manifest.json` in `smarter-api` first.
- Use `make react-build` (npm build, collectstatic, image build), not
  `make build`, after any React change. It is safe to run without asking:
  its output (`smarter/staticfiles/`, `smarter/smarter/static/react/`, the
  image) isn't tracked by git, and it touches no infrastructure. It returns when
  it's done, so run it in the foreground. Unlike `make run`, it doesn't
  restart the containers: follow it with `make run` in the background.
- The template tag caches a missing manifest for the life of the process, so
  restart `smarter-api` after fixing the static files.

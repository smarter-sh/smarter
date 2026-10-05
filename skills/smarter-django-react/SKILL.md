---
name: smarter-django-react
description: Use when building or changing a React app that Django serves in the Smarter web console, especially a resource list page (smarter-<kind>-list). Covers the Django view, template and templatetag that host the app, the root element's data attributes, SessionContext and fetchDjangoUrl in @smarter/common, the list/clone/rename/delete API contract, the Vite manifest build, and the sidebar link.
---

# Smarter Django + React

The web console is Django-rendered. Each interactive page embeds one React app,
built by Vite into Django's static files. The apps live in the npm workspace
`smarter/react/packages/`, and share code through `@smarter/common`.

## How a page is wired, end to end

```
sidebar link (context_processors.py)
  → Django view (views/listview/view.py) renders templates/react/<kind>-list.html with a context dict
    → template: {% load react_<kind>_list %} emits the Vite CSS/JS from manifest.json,
      plus <div id="smarter-<kind>-list-root" django-csrf-cookie-name=... smarter-<kind>-list-api-url=...>
      → main.tsx reads those attributes into a SessionContext and renders <App>
        → App POSTs to the list API with fetchDjangoUrl (CSRF + X-Smarter-* headers)
          → views/listview/api.py returns {"objects": [...]} serialized with can_delete, manifest_url
```

## The Django side

1. **View** (`<app>/views/listview/view.py`): a
   `SmarterAuthenticatedNeverCachedWebView` that renders
   `react/<kind>-list.html` with one context key, `<kind>_list`, containing:
   - `root_id`: `"smarter-<kind>-list-root"`
   - `django_csrf_cookie_name`, `django_session_cookie_name`, and
     `cookie_domain`, from `settings`
   - `<kind>_list_api_url`: `reverse(<App>ReverseNames.namespace, <App>ReverseNames.listview_api_all)`
   - `react_debug_mode`: the `ENABLE_REACTAPP_DEBUG_MODE` waffle switch
   - `smarter_request_id`: `self.generate_smarter_request_id()`
2. **Template tag** (`<app>/templatetags/react_<kind>_list.py`):
   `SmarterReactTemplateTagManager(app_name="@smarter/<kind>-list", templatetag_name=__name__)`.
   It reads `smarter/smarter/static/react/@smarter/<kind>-list/manifest.json`.
   The module defines a `@register.simple_tag` named `<kind>_list_react_assets`
   that returns `templatetag_manager.reactapp_build_assets`: the hashed CSS and
   JS file names.
3. **Template** (`smarter/smarter/templates/react/<kind>-list.html`): extends
   `dashboard/base.html`, emits the CSS in `style_extra` and the JS in
   `javascript_extra`, and renders the root `<div>`, with each context value as
   an attribute.
4. **List API** (`<app>/views/listview/api.py`), routed in `<app>/urls.py`:
   - `react-integration/api/listview/(owned|shared|all)/`: returns
     `{"objects": [...]}`, filtered by ownership. `?invalidate_cache=true`
     bypasses the cache.
   - `react-integration/api/clone/<id>/<new_name>/`,
     `.../rename/<id>/<new_name>/`, and `.../delete/<id>/`.
   - All are POSTs, scoped to what the user may read, own, or delete. A
     superuser sees every account's rows.
5. **Sidebar**: add the URL to `sidebar_context()` in
   `smarter/smarter/apps/dashboard/context_processors.py`, and the link to
   `smarter/smarter/templates/dashboard/sidebar.html`. Never leave the sidebar
   pointing at a placeholder.

## The React side

- **`main.tsx`** reads the root element's attributes, throws if a required one
  is missing, builds a `SessionContext`, and renders `<App sessionContext={...} />`.
  The root id and the API URL attribute name must match the template exactly.
- **`fetchDjangoUrl(sessionContext, url, requestJson)`**
  (`@smarter/common`, `lib/django.tsx`) POSTs with the `X-CSRFToken` header,
  read from the CSRF cookie, plus `X-Smarter-Client`,
  `X-Smarter-ClientVersion`, `X-Smarter-ClientType`, `X-Smarter-RequestId`, and
  `X-Smarter-Capabilities`. A new custom header must also be added to Django's
  `CORS_ALLOW_HEADERS` in `smarter/smarter/settings/base.py`.
- **`load()`** (`lib/load.tsx`) fetches `<ApiUrl>/<owned|shared|all>/?invalidate_cache=...`
  and reads `objects`.
- **`actionUrl(sessionContext, "clone/12/new_name/")`** turns the list URL into
  its sibling action URL.
- **`TabbedListView`** (`@smarter/common`) gives the owned/shared tabs. Lists
  are a `ListView` (table) plus a `CardView`, with a `Toolbar` and a
  `StatusBar`.
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
`smarter-guardrail-list` and `smarter-custom-domain-list` are the most recent.

1. `cp -R smarter/react/packages/smarter-guardrail-list smarter/react/packages/smarter-<kind>-list`
   (without `node_modules`, `dist`, `CHANGELOG.md`, or `.DS_Store`).
2. Rename it in `package.json` (`name`, `description`, and `config.s3BucketPath`),
   `index.html`, `main.tsx` (the root id, the API URL attribute, and its error
   messages), `lib/const.tsx`, and `README.md`.
3. Replace the `Types.tsx` object type, and the table columns and card fields,
   with the new serializer's fields.
4. Update the stories, the MSW fixtures and handlers, and the tests. See
   `smarter-react-testing`.
5. `make react-install`, then build: `cd smarter/react && npm run build -w @smarter/<kind>-list`.
   Vite writes the bundle and `manifest.json` into
   `smarter/smarter/static/react/@smarter/<kind>-list/`, which isn't committed.
   Copy it into `smarter-app` (`smarter-docker-environment`) to see it in the
   console.

See [references/canonical-django-react-reference.md](references/canonical-django-react-reference.md)
for the files to read.

# Web console SPA migration: inventory and plan

Working tracker for [ADR-035](source/adr/035-single-page-app.rst). It lists every console page,
what it needs from the backend, where it goes, and in which phase. Delete this file when the
repository splits.

Paths are relative to `smarter/smarter/` (Django) and `smarter/react/packages/` (React) unless they
start with `docs/` or `helm/`. "Ctx" is data from the database or settings, which needs JSON. URLs,
cookie names and element ids become frontend constants and aren't listed.

## Phases

| #   | Phase                | Done when                                                                                                                                                                                 |
| --- | -------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0   | Clean up             | Dead pages and templates deleted, duplicate mounts removed, security fixes in (see [Delete](#delete) and [Bugs](#bugs-found-along-the-way))                                               |
| 1   | Foundation           | `@smarter/console` builds and runs; `/api/web/session/`; the app shell (header, sidebar, user menu, footer); sign-in and the account flows; Django serves `index.html` for migrated paths |
| 2   | Existing React pages | Dashboard, list pages, manifest detail pages, workbench, extensions, drop zone, terminal, passthrough are SPA routes                                                                      |
| 3   | Docs pages           | `/docs/` pages are SPA routes; schemas, examples and `openapi.json` come from `/api/v1/`                                                                                                  |
| 4   | Separate hosts       | Backend at `api.<platform>`, SPA static on a CDN, shared cookie domain, CSRF, CORS, ingress                                                                                               |
| 5   | Split the repository | Console and backend in separate repositories; Helm, CI and skills follow                                                                                                                  |

Phase 0 can ship to `alpha` on its own, and so can each page in phases 1 to 3.

**Phase 0 status.** Done: everything under [Delete](#delete), except `/account/activation/` and
`/workbench/llm-clients/<id>/` (see below), and bugs 1, 2, 3, 6, 7 and 13. Left for the endpoints
that replace the views in phase 1: bugs 4 (side effects on GET) and 5 (rate limit). The frame bugs
(8 to 12, 14 to 16) go away with the templates in phases 1 and 2.

- `/account/activation/` stayed until phase 1 decided what follows a self-registration: it is deleted.
- `/workbench/llm-clients/<id>/` is not dead: the workbench passes it to Smarter Chat, which
  appends `config/`. It moves with the workbench endpoints in phase 2.

**Phase 1 status.** Done: `GET /api/web/session/` with its contract; `@smarter/console` with React Router,
the session provider, the sign-in guard, a first shell, and generated contract types; the account api
(`login/`, `logout/`, `register/`, `password-reset-request/`, `password-reset/<uidb64>/<token>/`) with
the per-address credentials rate limit, which closes bug 5; and the console's sign-in, sign-up, sign-out
and password reset pages, with the Doodle. Django serves the console's `index.html` at `/login/`,
`/register/`, `/password-reset-request/` and `/password-reset-link/<uidb64>/<token>/`
(`smarter.apps.dashboard.views.console_app`), and their Django views, templates, scripts and the doodle's
template tag are deleted.

Email verification: a sign-up creates an inactive user and emails an activation link
(`smarter.apps.account.activation`, sharing `smarter.apps.account.email_links` with password reset). The
account api adds `activate/<uidb64>/<token>/` (POST, signs in) and `activation-resend/`, and sign-in answers
403 for the right password of an account that is waiting. The console serves `/account/activate/...`,
`/account/inactive/` and `/account/already-associated/`, and their Django views and templates are deleted,
with `/account/activation/`. The user menu signs out with `POST /api/web/account/logout/`, and Django's
`/logout/` is gone, which closes bug 4.

The frame: the console's signed-in pages have the sidebar and the user menu, in the theme's own app layout
(`Layout`, `components/Sidebar`, `components/Header`, `lib/theme`). The session api sends the sidebar's links
(`ConsoleSidebar`), null for those the platform or user doesn't have. The user menu is
`@smarter/dashboard-user-menu`'s `UserMenu`, which the package now exports; the console builds its context from
the session (`lib/userMenu`). Until a page moves into the console, its link is the backend's page.

The user menu's endpoints moved from `/account/dashboard/` to the account api: `profile-image/`,
`user-profiles/` (now a `GET`) and `user-profiles/select/`, in `smarter.apps.account.api.web.profile_image` and
`user_profiles`. The old paths answer 404.

The dashboard is the console's: `/dashboard` renders `@smarter/dashboard`'s `Dashboard` (now an import-only package,
with no build) inside the frame, and `/` redirects to it. Django serves the console at `/dashboard/`, keeping the
name `dashboard:dashboard`; `DashboardView`, `react/dashboard.html` and the `react_dashboard` template tag are
deleted, which closes bug 10. The sidebar opens the console's pages in place (`CONSOLE_PAGE_PATHS`). Tests of
Django's frame use `SERVER_RENDERED_PAGE`.

The console's frame now has what Django's has: the welcome dialog (`@smarter/welcome`, now importable) with its
sidebar hint and the onboarding state from the session, the Did you know? tip, and a theme mode menu that stores the
choice where the theme's JavaScript does, so the console and Django's pages share it. The dashboard route loads
lazily, in its own chunk.

The resource lists (section 3, phase 2) are the console's, all sixteen. Each `@smarter/<kind>-list` is import-only,
and the console's `lib/lists` (`LIST_PAGES`) gives each a lazy route at Django's path without the slash, with a
session context whose `ApiUrl` is the list api, the onboarding state (the LLMClient list's weather hint), and a
`visible` rule where the backend limits the page: proxies and vectorstores while their feature is on, the
infrastructure resources for superusers. Django keeps each `<Kind>ListView`, now a `ConsoleAppView` subclass, so
that `listview_registry()` still pairs the page with its list api for the global search; the templates and
template tags are deleted, and `ResourceViewsTestMixin` checks that each list page is the console's. Tests of
Django's frame use `SERVER_RENDERED_PAGE`, now the Extensions console. The courses link the deleted files at
release v0.42.10, and `skills/smarter-django-react` teaches the console's lists.

The Extensions console is the console's too: `/extensions` and `/extensions/:slug` render
`@smarter/extension-console` (now import-only) with `canEdit` from the session and the router's `navigate`. The api
refuses an extension that the user's account may not use, as Django's detail view did. Django keeps
`ExtensionListView` and `ExtensionDetailView` as `ConsoleAppView` subclasses; the templates and the template tag are
deleted. `SERVER_RENDERED_PAGE` is the Prompt Passthrough.

The manifest pages (section 4) are the console's, but the LLMClient's, which moves with the workbench (section 5):
`lib/manifestPages` (`MANIFEST_PAGES`) routes each existing path to `ManifestPage`, which reads the resource from
`/api/web/dashboard/resource/<record locator>/`, a new route that infers the kind (`kind_of_instance()`), and renders
`@smarter/manifest-editor`; after a delete it goes back to the list. The open question is answered: the api's
`readable_instance()` is the detail views' three-step lookup, plus every resource for a superuser, less what
`restrict_readable` hides, and across all of a user's profiles; Secrets use the same rule in both. Budgets had no
rule in the api, so any signed-in user could read any Budget there: `readable_instance()` now asks the model's
`is_readable_by()` when its manager has no read rule, and reads nothing for a model with neither, and
`Budget.is_readable_by()` is the old page's rule. The api describes the resource as its owner, as the lists' detail
dialogs already did, and an ownerless one, a Budget, as its reader, as the old page did. The fifteen detail views are `ConsoleAppView`
subclasses; `common/manifest_detail.html`, the editor's template tag and `DocsBaseView` stay for the workbench.
Next: the workbench and the other React pages (section 5).

The manifest drop zone, the Prompt Passthrough and the Terminal (section 5, step 1) are the console's. Their
packages, `@smarter/drop-zone`, `@smarter/prompt-passthrough` and `@smarter/terminal-emulator`, are import-only, each
with a `./mocks` export; the console's `routes/ToolPages` renders them at `/dashboard/dropzone`,
`/dashboard/passthrough` and `/dashboard/terminal`, with their urls from `lib/tools`, and shows Page not found while
the session's flag is off (`manifestDropZone`, `passthrough`, `terminal`, which is on for a superuser only); the
Passthrough's Server Logs tab follows `serverLogs`. Django keeps `DropzoneView`, `PromptPassthroughView` and
`TerminalEmulatorView` as `ConsoleAppView` subclasses, the Terminal's still behind `require_terminal`, and their urls
are still registered only while their settings are on. The three templates and template tags are deleted, and the
Django-React guide's worked example is now the workbench, the one page Django still hosts that way. Its pages, and
the LLMClient's manifest page, are the last in Django's frame, and each needs an LLMClient, so `SERVER_RENDERED_PAGE`
is gone: tests of the frame call `get_server_rendered_page()` (`smarter.lib.unittest.server_rendered_page`), which
renders `dashboard/base.html` alone, at a path of a test-only urlconf that adds it to the console's. Next: the
workbench's endpoints (section 5, step 2).

The workbench's endpoints (section 5, step 2) are in the apis. Its chat's `apiUrl` is the LLMClient in the public
api, `/api/v1/llm-clients/<hashed_id>/`, whose `config/` is the same `PromptConfigView`; prompts already went to
`/api/v1/llm-clients/<hashed_id>/prompt/` (`url_llmclient`). Compared for the same user, LLMClient and host, the two
configurations differ only in `sandbox_mode` and `meta_data.is_authentication_required`, which a workbench url sets
to true; neither the chat nor the workbench reads them, and both routes refuse an anonymous visitor alike.
`/workbench/llm-clients/<hashed_id>/config/` is still routed, and `/workbench/llm-clients/<hashed_id>/` is still the
always-404 base of `sandbox_url`, which the api reports. The Manifest, Architecture and Deployment tabs' endpoints and
the api key actions moved to `/api/web/prompt/llm-clients/<hashed_id>/` (`manifest/`, which was `manifest/editor/`,
`architecture/`, `deployment/` and `deployment/api-keys/{create,attach,detach}/`), named in
`PromptApiWebReverseNames`; the old paths answer 404. They keep their methods (GET for the three tabs). Next: the
workbench and the LLMClient's manifest page in the console (section 5, step 3).

Checking the workbench's access rule before step 3 found that the LLMClient's manifest page and the Manifest tab's
endpoint described any LLMClient to any signed-in user, another account's and staff-only ones included (released
since v0.33.5). That was fixed first, on its own: both now refuse a user who may not read the LLMClient with the
resource api's rule.

The workbench and the LLMClient's manifest page (section 5, step 3) are the console's, so every console page is.
`@smarter/workbench` is import-only (`Workbench`, `WorkbenchConfig`, a `./mocks` export, a development page; its
styles are imported by `App`), and `WorkbenchConfig` has an optional `navigate`, which its Manifest tab uses after
a delete. The console's `routes/WorkbenchPage` renders it lazily at `/workbench/llm-clients/:id/prompt`, configured
by `lib/workbench` from the hashed id and the session, after asking the resource api for `llmclient-<id>`: a 404
shows Page not found. That is stricter than Django's page, which opened for any signed-in user (with no data for
one who may not read the LLMClient). `lib/useResource` is that request, shared with `ManifestPage`. The LLMClient's
manifest page is one more `MANIFEST_PAGES` entry, `/workbench/llm-clients/:id/manifest`. Django's
`PromptWorkbenchView` and `LLMClientDetailView` are `ConsoleAppView` subclasses; the Manifest tab's endpoint,
`LLMClientManifestEditorView`, uses `readable_llmclient()` and the resource api's `manifest_yaml()`, instead of a
brokered request through `DocsBaseView`. `react/workbench.html`, `common/manifest_detail.html`,
`common/manifest_editor.html`, the `react_workbench` and `react_manifest_editor` template tags are deleted, and the
Django-React guide describes the console. `DocsBaseView` stays for the docs pages. Next: Django's console frame
(section 5, step 4).

Django's console frame is retired (section 5, step 4), which finishes section 5 and phase 2: every console page,
and its frame, is the console's. Deleted: `templates/dashboard/` (base, header, sidebar, footer, navbar), the
`templates/react/` widgets (user menu, Did you know?, onboarding, welcome) and their template tags, the `sidebar`
context processor and `active_sidebar_item()`, `onboarding_context()`, and `smarter.lib.unittest.server_rendered_page`.
`sidebar_context()` stays, for the session api and the dashboard's quick actions; the `base`, `branding` and
`footer` processors stay for `base.html` and the docs pages' frame (`cms/base.html`). The frame's tests moved to
what the console reads: the session api's tests check the onboarding state, the Did you know? switch, the welcome
dialog after a dismiss, the selected profile's account and the Budgets link; the console's `index.html` loads the
JavaScript catalog. `@smarter/dashboard-user-menu`, `@smarter/welcome` and `@smarter/manifest-editor` are
import-only, and `@smarter/didyouknow` keeps only its library build. The template-tag pattern remains for one page
outside the console, a deployed LLMClient's host's (`llmclient/endpoints.html`, `@smarter/llmclient-deployment`),
and the Django-React guide uses it as that pattern's example. `@smarter/onboarding` still falls back to a JSON
`<script id="smarter-onboarding">` when no state is passed; no page writes one now. Next: the docs pages (section 6,
phase 3).

The docs pages' backend (section 6, step 1): the api serves its OpenAPI document at `/api/v1/openapi.json`
(`smarter.apps.api.v1.contract.views`, `ApiV1ReverseNames`), with the platform's own server first, as before, and
`/docs/openapi.json` redirects there permanently, keeping its query string, because the SDK docs and generated
clients use it. The Scalar page reads the api's address. The session lists every SAM kind (`samKinds`, sorted), for
the docs pages' lists of example manifests and JSON Schemas, which call the public cli api,
`/api/v1/cli/example-manifest/<kind>/` and `json-schema/<kind>/`. Next: the docs pages in the console (step 2).

The docs pages are the console's (section 6, steps 2 and 3, done together, so that no Django page pointed at the moved
Scalar), which finishes phase 3. They are public, in their own frame (`routes/DocsLayout`: the docs' links, the theme
mode menu, Sign In or Dashboard, and the project's tools beside a page), lazily loaded: `/docs/manifests` and
`/docs/json-schemas` list the session's `samKinds`, `/docs/manifest/:kind` and `/docs/json-schema/:kind` read the
public cli api and show YAML or JSON with `@smarter/common`'s `CodeBlock` (now exported, with its own stylesheet), and
`/docs/openapi` loads Scalar, now in the console's `public/scalar/`, on its first visit (`lib/scalar`). The landing
pages' copy was rewritten plainly, without the old sales language, and translated. The sidebar opens the three docs
pages in place. Django's 50 per-kind views and url names became two routes, `manifest/<str:kind>/` and
`json-schema/<str:kind>/`, `ConsoleAppView` subclasses that answer 404 for a kind that isn't one; the landing and
OpenAPI pages keep their url names. The per-kind pages no longer need a sign-in, as the api they show never did.
Deleted: `DocsBaseView` and its brokered requests, `templates/docs/`, the docs frame `templates/cms/` and
`static/cms/`, and `smarter-base.js`'s sign-out handler, which only the docs menu used; that closes bug 12 (the menu's
`/docs/cli` link). `generate_example_manifests` writes every kind's example from `sam_example()`. A new SAM kind needs
no docs code. Next: phase 4, separate hosts.

## Development

- The SPA is `@smarter/console` (`smarter/react/packages/smarter-console`). Run it with
  `npm run dev -w @smarter/console` in `smarter/react`, then open `http://localhost:5173/`.
- Vite proxies `/api/`, `/admin/`, `/social-auth/`, `/static/`, `/jsi18n/`, `/i18n/` and `/ws/` to
  `http://localhost:9357/`, so the session and CSRF cookies are first-party.
- The Django console keeps running at `http://localhost:9357/` for pages not yet migrated.

## 1. The frame: context processors and the session endpoint

`GET /api/web/session/` replaces these. It's a GET, so it needs no CSRF token, and it sets the CSRF
cookie (`ensure_csrf_cookie`). The user-menu template tag
(`apps/dashboard/templatetags/react_dashboard_user_menu.py:66-128`) already computes most of the
signed-in part and is the starting point.

| Context processor (`settings/base.py:1068-1080`)                 | Keys the SPA still needs                                                                                     | Becomes                           |
| ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ | --------------------------------- |
| `django...auth`                                                  | `user`                                                                                                       | `session.user`                    |
| `django...i18n`                                                  | `LANGUAGE_CODE`, `LANGUAGES`, `LANGUAGE_BIDI`                                                                | `session.language`                |
| `apps/account/context_processors.base`                           | `account_authenticated.account`                                                                              | `session.account`                 |
| `apps/dashboard/context_processors.base` (:294)                  | names, email, `profile_image_url`; `is_proxy_enabled`, `is_vectorstore_enabled`, `is_file_drop_zone_enabled` | `session.user`, `session.flags`   |
| `apps/dashboard/context_processors.branding` (:391)              | settings-driven branding fields (list below)                                                                 | `session.branding`                |
| `apps/dashboard/context_processors.sidebar` (:254)               | `extension_updates` (superusers); which feature-gated links show                                             | `session.badges`, `session.flags` |
| `apps/dashboard/context_processors.footer` (:478)                | `about_url`, `support_url`, `legal_url`, `contact_url`                                                       | `session.branding`                |
| `static_version`, `cache_buster`, `debug`, `messages`, `request` | none                                                                                                         | dropped                           |

**`session` fields**

- **Anonymous:** `branding`, `auth` (Google and GitHub enabled, sign-up enabled, footer links
  enabled), `flags.doodle`, `language`, `version`, `isAuthenticated: false`.
- **`user`:** username, email, first and last name, `isSuperuser`, `isStaff`, `profileImageUrl`,
  `userProfileCount`.
- **`account`:** account number, name, selected user profile.
- **`flags`** from `smarter_settings`: `enable_proxy`, `enable_vectorstore`,
  `enable_dropzone_manifest_apply`, `enable_web_console_terminal` (and superuser),
  `enable_dashboard_passthrough_prompt`, `enable_dashboard_server_logs`.
- **`flags`** from waffle switches: `enable_reactapp_debug_mode`, `enable_web_console_did_you_know`,
  `enable_web_console_onboarding_hints`, `enable_web_console_server_logs`,
  `enable_account_registration`, `enable_oauth2`, `enable_login_footer_links`, `enable_doodle`.
- **`onboarding`:** `enabled`, `seen[]`. Replaces the `json_script` in `react/onboarding.html`.
- **`welcome`:** `show`, `showAtStartup`, `firstName`. `show` depends on a session key the welcome
  API doesn't return today.
- **`badges`:** `extensionUpdates`.
- **`branding`:** corporate name and address, support email, phone and hours, primary contact,
  contact URL, copyright, Facebook, Twitter, LinkedIn and Slack URLs, logo, marketing site, project
  website, docs and CDN URLs, environment URL.
- **`cookies`:** CSRF and session cookie names, cookie domain. Or compile them into the build.

`branding()` must survive as a helper: `apps/account/models/account.py:91-106` builds the welcome
email from it.

**Frame templates that go:** `base.html` (except as the email layout, see Bugs), `dashboard/base.html`,
`dashboard/header.html`, `dashboard/navbar.html`, `dashboard/navbar/theme-mode-menu-item.html`,
`dashboard/sidebar.html`, `dashboard/footer.html`, `common/cookie-notice.html`, `400`/`403`/`404`/`500.html`
(the API already answers JSON errors through `SmarterJsonErrorMiddleware`).

**Frame widgets that become app shell components:** `@smarter/dashboard-user-menu`,
`@smarter/didyouknow`, `@smarter/welcome`, `@smarter/onboarding`.

## 2. Sign-in and the account

All of these host `@smarter/doodle` in their left panel through `account/authentication/base.html:91`.
The forms are Django forms defined inside their views.

| Path                                                  | View                                                 | Ctx                                                    | POST does                                                | SPA route                    | New endpoint                                                   | Phase |
| ----------------------------------------------------- | ---------------------------------------------------- | ------------------------------------------------------ | -------------------------------------------------------- | ---------------------------- | -------------------------------------------------------------- | ----- |
| `/login/` (moved)                                     | `apps/account/views/authentication/login_view.py:38` | OAuth providers, sign-up and footer switches, branding | looks up email, `authenticate`, `login`, 302 `/`         | `/login`                     | `POST /api/web/account/login/`                                 | 1     |
| `/logout/` (+ `/account/logout/`)                     | `authentication/logout_view.py:21`                   | —                                                      | `logout` on GET or POST                                  | —                            | `POST /api/web/account/logout/`                                | 1     |
| `/register/` (moved)                                  | `authentication/account_views.py:65`                 | —                                                      | creates the user, signs in, 302 to a missing `/welcome/` | `/register`                  | `POST /api/web/account/register/`, gated by the switch         | 1     |
| `/password-reset-request/` (moved)                    | `views/password_management.py:36`                    | —                                                      | builds a token link, sends the reset email               | `/password-reset-request`    | `POST /api/web/account/password-reset-request/`                | 1     |
| `/password-reset-link/<uidb64>/<token>/` (moved)      | `password_management.py:109`                         | token check                                            | sets the password, 302 `/login/`                         | same path (emailed)          | `GET`/`POST /api/web/account/password-reset/<uidb64>/<token>/` | 1     |
| `/account/activate/<uidb64>/<token>/`                 | `account_views.py:221`                               | token check                                            | GET sets `is_active`                                     | same path (emailed)          | `POST /api/web/account/activate/<uidb64>/<token>/`             | 1     |
| `/account/inactive/`                                  | `account_views.py:42`                                | branding                                               | —                                                        | same path (social pipeline)  | none                                                           | 1     |
| `/account/already-associated/`                        | `authentication/social_auth.py:16`                   | branding                                               | —                                                        | same path (middleware)       | none                                                           | 1     |
| `/account/dashboard/profile-image/`                   | `views/dashboard/profile_image.py:53`                | —                                                      | already JSON: upload or delete                           | —                            | move to `/api/web/account/profile-image/`                      | 1     |
| `/account/dashboard/user-profiles/`                   | `views/dashboard/user_profiles.py:117`               | —                                                      | already JSON, POST used as a read                        | —                            | `GET /api/web/account/user-profiles/`                          | 1     |
| `/account/dashboard/user-profiles/select/`            | `user_profiles.py:156`                               | —                                                      | already JSON: selects the profile in the session         | —                            | `POST /api/web/account/user-profiles/select/`                  | 1     |
| `/i18n/setlang/`                                      | Django `set_language`                                | —                                                      | sets the language cookie, 302 `next`                     | —                            | `POST /api/web/account/language/` (or keep)                    | 1     |
| `/dashboard/profile/`, `/dashboard/profile/language/` | `apps/dashboard/views/profile/profile.py:10,16`      | —                                                      | template only                                            | check if linked; else delete | —                                                              | 0/1   |

**Stays on the backend:** `/social-auth/...` (OAuth redirects; the SPA links to
`/social-auth/login/<backend>/`), `/account/unsubscribe/<token>/` (mail providers POST to it),
`/account/email/*` (local-only email previews), every email template.

**Emailed links** (`lib/django/token_generators.py:80-112`): `/password-reset-link/...`,
`/account/activate/...`, `/account/unsubscribe/...`, `/login/`, `/workbench/`. The first two and the
last two must exist as SPA routes.

## 3. Resource list pages

Each is `templates/react/<kind>-list.html` plus a `react_<kind>_list` template tag and a list view on
`SmarterAuthenticatedNeverCachedWebView`. Every API is already under `/api/web/`. Twelve packages'
`App.tsx` differ from guardrail's by 2 to 12 lines; they become one generic `/:kind` list route with a
per-kind configuration. Phase 2.

| Path                         | View                                          | Package                                | API                                           | Gate                  |
| ---------------------------- | --------------------------------------------- | -------------------------------------- | --------------------------------------------- | --------------------- |
| `/authtoken/`                | `lib/drf/views/listview/view.py:17`           | authtoken-list                         | `/api/web/authtoken/listview/`                |                       |
| `/budget/`                   | `apps/account/views/budget/listview.py:73`    | budget-list (outlier)                  | `/api/web/account/budget/listview/`           | delete: superuser     |
| `/connection/`               | `apps/connection/views/listview/view.py:20`   | connection-list                        | `/api/web/connection/listview/`               |                       |
| `/llmclient/custom-domains/` | `apps/llmclient/views/listview/view.py:20`    | custom-domain-list                     | `/api/web/llmclient/custom-domains/listview/` |                       |
| `/guardrail/`                | `apps/guardrail/views/listview/view.py:21`    | guardrail-list (reference)             | `/api/web/guardrail/listview/`                |                       |
| `/infrastructure/`           | `apps/infrastructure/views/listview.py:110`   | infrastructure-resource-list (outlier) | `/api/web/infrastructure/listview/`           | superuser             |
| `/workbench/`                | `apps/prompt/views/listview/view.py:27`       | llmclient-list (outlier)               | `/api/web/prompt/listview/`                   |                       |
| `/llmhost/`                  | `apps/llmhost/views/listview/view.py:21`      | llmhost-list                           | `/api/web/llmhost/listview/`                  |                       |
| `/llmhost/compute/`          | same file `:82`                               | llmhost-compute-list                   | `/api/web/llmhost/compute/listview/`          |                       |
| `/llm-tools/`                | `apps/llmtool/views/listview/view.py:21`      | llmtool-list                           | `/api/web/llmtool/listview/`                  | `/plugin/*` redirects |
| `/mcpclient/`                | `apps/mcpclient/views/listview/view.py:21`    | mcpclient-list                         | `/api/web/mcpclient/listview/`                |                       |
| `/orchestrator/`             | `apps/orchestrator/views/listview/view.py:21` | orchestrator-list                      | `/api/web/orchestrator/listview/`             |                       |
| `/provider/`                 | `apps/provider/views/listview/view.py:21`     | provider-list                          | `/api/web/provider/listview/`                 |                       |
| `/proxy/`                    | `apps/proxy/views/listview/view.py:21`        | proxy-list                             | `/api/web/proxy/listview/`                    | `enable_proxy`        |
| `/secret/`                   | `apps/secret/views/listview/view.py:21`       | secret-list                            | `/api/web/secret/listview/`                   |                       |
| `/vectorsearch/`             | `apps/vectorsearch/views/listview/view.py:21` | vectorsearch-list                      | `/api/web/vectorsearch/listview/`             |                       |
| `/vectorstore/`              | `apps/vectorstore/views/listview/view.py:21`  | vectorstore-list                       | `/api/web/vectorstore/listview/`              | `enable_vectorstore`  |
| `/extensions/`               | `apps/llmtool/extension/views.py:304`         | extension-console                      | `/api/web/llmtool/extensions/`                | edit: superuser       |

## 4. Manifest detail pages

All 17 render `common/manifest_detail.html` with `@smarter/manifest-editor`, through `DocsBaseView`
(`apps/docs/views/base.py:110`). Each view is about 150 copied lines that resolve `hashed_id`, look up
the object (owner, then account admin, then Smarter admin), call the CLI describe view in-process,
and embed the YAML. They become one generic `/:kind/:locator` route that reads
`/api/web/dashboard/resource/<kind>/<record_locator>/` (which already returns the manifest YAML) or
`POST /api/v1/cli/describe/<kind>/`. The old paths stay as router aliases. Phase 2.

Open question, answered in phase 2: `readable_instance()` allows the detail views' three-step lookup, plus every
resource for a superuser, less what `restrict_readable` hides, and across all of a user's profiles.

Paths: `/authtoken/<uuid>/`, `/budget/budgets/<id>/`, `/connection/connections/sql-connection/<id>/`,
`/connection/connections/api-connection/<id>/`, `/guardrail/guardrails/<id>/`,
`/llmclient/custom-domains/<id>/`, `/llmhost/llmhosts/<id>/`, `/llmhost/compute/<id>/`,
`/llm-tools/plugins/<id>/`, `/mcpclient/mcpclients/<id>/`, `/orchestrator/orchestrators/<id>/`,
`/provider/providers/<id>/`, `/proxy/proxies/<id>/`, `/secret/secrets/<id>/`,
`/vectorsearch/vectorsearchs/<id>/`, `/vectorstore/vectors/<id>/`,
`/workbench/llm-clients/<id>/manifest/`.

## 5. Workbench and the other React pages

| Path                                  | View                                                    | Package            | Ctx                                            | SPA route                           | Phase |
| ------------------------------------- | ------------------------------------------------------- | ------------------ | ---------------------------------------------- | ----------------------------------- | ----- |
| `/dashboard/`                         | `apps/dashboard/views/views/dashboard.py:46`            | dashboard          | none (8 `/api/web/dashboard/` URLs)            | `/dashboard`                        | 2     |
| `/workbench/llm-clients/<id>/prompt/` | `apps/prompt/views/.../prompt_workbench_view.py:205`    | workbench          | server-logs flag; the rest derives from `<id>` | `/workbench/llm-clients/:id/prompt` | 2     |
| `/extensions/<slug>/`                 | `apps/llmtool/extension/views.py:321`                   | extension-console  | `canEdit` (superuser)                          | `/extensions/:slug`                 | 2     |
| `/dashboard/dropzone/`                | `apps/dashboard/views/dropzone/view.py:45`              | manifest-dropzone  | `enable_dropzone_manifest_apply`               | `/dashboard/dropzone`               | 2     |
| `/dashboard/terminal/`                | `apps/dashboard/views/terminal_emulator/reactapp.py:40` | terminal-emulator  | flag and superuser; WebSocket `ws/terminal/`   | `/dashboard/terminal`               | 2     |
| `/dashboard/passthrough/`             | `apps/dashboard/views/passthrough/view.py:46`           | prompt-passthrough | flag; server-logs flag                         | `/dashboard/passthrough`            | 2     |

**Workbench endpoints outside `/api/web/`** (phase 2, before the workbench route):

| Endpoint                                                                  | Becomes                                                                                                    |
| ------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| `/workbench/llm-clients/<id>/config/` (chat)                              | `/api/v1/llm-clients/<id>/config/` if the responses match; else `/api/web/prompt/llm-clients/<id>/config/` |
| `/workbench/llm-clients/<id>/manifest/editor/`                            | `/api/web/prompt/llm-clients/<id>/manifest/`                                                               |
| `/workbench/llm-clients/<id>/architecture/`                               | `/api/web/prompt/llm-clients/<id>/architecture/`                                                           |
| `/workbench/llm-clients/<id>/deployment/`                                 | `/api/web/prompt/llm-clients/<id>/deployment/`                                                             |
| `/workbench/llm-clients/<id>/deployment/api-keys/{create,attach,detach}/` | `/api/web/prompt/llm-clients/<id>/deployment/api-keys/...`                                                 |

**Not part of the SPA:** the page a deployed LLMClient's host shows at `/`
(`apps/llmclient/views/endpoints.py:409`, `llmclient/endpoints.html`, `@smarter/llmclient-deployment`).
It stays a standalone bundle on the backend.

## 6. Docs pages (phase 3)

| Path                                      | Today                                        | Becomes                                                                 |
| ----------------------------------------- | -------------------------------------------- | ----------------------------------------------------------------------- |
| `/docs/`                                  | redirect to `/docs/manifests/`               | SPA redirect                                                            |
| `/docs/manifests/`, `/docs/json-schemas/` | copy plus the kind list                      | SPA pages                                                               |
| `/docs/manifest/<kind>/` (25)             | wraps `/api/v1/cli/example-manifest/<kind>/` | SPA route calling that API                                              |
| `/docs/json-schema/<kind>/` (25)          | wraps `/api/v1/cli/json-schema/<kind>/`      | SPA route calling that API                                              |
| `/docs/openapi/`                          | Scalar page                                  | SPA route rendering Scalar                                              |
| `/docs/openapi.json`                      | the committed contract, servers rewritten    | `/api/v1/openapi.json`; `/docs/openapi.json` redirects (documented URL) |
| `/docs/developer/*` (8)                   | repository files; linked only from tests     | delete (phase 0), with the three `Dockerfile` `COPY` lines              |

Update the sensitive-file amnesty patterns for `/docs/manifest` and `/docs/json-schema`
(`common/conf/defaults.py:198`, and smarter-deploy's `.env.example`).

## 7. Stays on the backend

`/api/v1/`, `/api/web/`, `/admin/`, `/admin/docs/`, `/social-auth/`, `/account/unsubscribe/<token>/`,
`/account/email/*` (local only), `/healthz/`, `/readiness/`, `/jsi18n/` (until the SPA loads catalogs
another way), `/static/`, `ws/terminal/`, `/prompt/` and `/config/` (custom domains), deployed
LLMClient hosts (`urls/llmclients.py`), `robots.txt`, `sitemap.xml`, favicons, `rest_framework/api.html`,
email templates and `branding()` as the email helper.

## Delete

Phase 0, each with its views, templates, static JS and tests:

- `deprecated_urlpatterns` in `apps/account/views/dashboard/urls.py:93-152` (overview, settings,
  activity, logs, users, billing, statements, api-keys) and their templates in
  `account/dashboard/`.
- `account/dashboard/secret.html`, `secrets.html` (no view).
- `/account/api-keys/` (orphaned; the `/authtoken/` page replaces it).
- `/account/users/` and `/account/user/<id>/` (orphaned; see Bugs).
- `/account/deactivate/` (deactivates nothing).
- `/account/activation/` (unreachable: it requires sign-in, which inactive users can't do).
- `/password-confirm/` (nothing links to it).
- `account/authentication/email/welcome-message.html`, `password-reset-sent.html` (unused).
- `coming-soon.html`, `dashboard/email-added.html` and their views (unrouted).
- `dashboard/json-schema.html`, `cms/base/sidebar.html` (unused).
- `/docs/developer/*` (see section 6).
- `/workbench/llm-clients/<id>/` (always 404; exists so `sandbox_url` reverses).
- Duplicate mounts: `/dashboard/account/` (all of `account/` again), `/dashboard/plugins/` (all of
  `llm-tools/` again), `/account/login/`, `/account/logout/`, `/account/register/`.

## Bugs found along the way

Security first. Fix these in phase 0 or in the endpoint that replaces the view.

1. **Privilege escalation.** `/account/user/<id>/` (`apps/account/views/dashboard/users.py:19-30`) is
   live, and its form edits every `User` field except `password` and `date_joined`, so a staff user
   can set `is_superuser` and `is_staff`. Delete it in phase 0.
2. **Open registration.** `/register/` accepts sign-ups whatever `ENABLE_ACCOUNT_REGISTRATION` says;
   only the link on the sign-in page is hidden.
3. **Account enumeration.** Login answers "Unknown user <email>" with a 403 for unknown addresses
   (`login_view.py:248`), and 400 for a wrong password.
4. **Side effects on GET.** Logout and account activation act on GET. Fixed in phase 1: both are POSTs
   to the account api.
5. **No rate limit** on password reset requests.
6. **`/register/` redirects to `/welcome/`,** which doesn't exist.
7. **The sign-in page's JS expects 401** for a wrong password, but the view returns 400, so nothing
   is shown.
8. **Emails link home with a relative URL** (`{% url 'console_home' %}` in the password-reset and
   activation emails), which doesn't work in a mail client.
9. **`branding()` caches request values:** `canonical` and `root_url` keep the first request's
   values for the cache's lifetime.
10. **The dashboard caches its whole context,** including `smarter_request_id`
    (`apps/dashboard/views/views/dashboard.py:85-138`). Fixed in phase 1: the console serves the dashboard.
11. **Dead template keys:** `dashboard.debug_mode` and `dashboard.smarter_version` are never set, so
    `window.debugMode` is always false and the sidebar's changelog label has no version.
12. **`/docs/cli`** is linked from the docs menu (`cms/base/menu/cli.html`) and has no route.
13. **`DocsBaseView.post`** answers "PATCH method not supported".
14. **The authtoken list never receives its debug flag:** the template emits `smarter-debug-mode`,
    the app reads `react-debug-mode`.
15. **`footer.contact_url`** is a hard-coded personal URL (`context_processors.py:478`).
16. **`400.html` always says "Forbidden."** instead of the response's message, so every 400 page
    shows the wrong text.

## Phase 4 findings: separate hosts

- **Cookies.** `SESSION_COOKIE_DOMAIN` and `CSRF_COOKIE_DOMAIN` are `environment_platform_domain`
  (`settings/base.py:251,403`), not a parent domain, so they don't reach `api.<platform>`. A parent
  domain must not leak into deployed LLMClient hosts under `*.api.platform.<root>`.
- **Host routing.** `hosts.py` matches `api.<root>` and `<env>.api.<root>`, but on AWS the api domain
  is `<env>.api.platform.<root>`, so the api host is served by the console urlconf today. Verify on a
  deployed host.
- **CSRF.** `CSRF_TRUSTED_ORIGINS` in `settings/base.py:308` has no scheme (AWS and local override it).
- **CORS.** `CORS_ALLOWED_ORIGIN_REGEXES` are hard-coded to `smarter.sh` patterns that don't match
  `api.platform.smarter.sh`. Traefik's CORS middleware on the platform and api ingresses
  (`../smarter-infrastructure/aws/terraform/smarter/templates/traefik-middleware-cors.yaml.tpl`)
  answers before Django.
- **Ingress.** No ingress in `helm/`; both are in smarter-infrastructure
  (`kubernetes-ingress.tf:19-50`) and send every path on each host to Django.
- **WebSocket.** `ws/terminal/` checks `AllowedHostsOriginValidator`; the SPA's origin must be allowed.
- **Cookie flags.** `SESSION_COOKIE_HTTPONLY=False` and `CSRF_COOKIE_SECURE=False` on AWS
  (`base_aws.py:75,80`). The SPA doesn't need to read the session cookie, so it can be HttpOnly.

## Translations

- The `.po` pipeline stays. Strings in the frame templates (header, sidebar, footer, cookie notice,
  error pages) move from `django.po` to `djangojs.po` as React `gettext()` calls.
- The SPA loads its catalog before rendering: keep `/jsi18n/`, or compile `djangojs.po` to JSON at
  build time.
- The SPA sets `<html lang>` and `dir` itself.

## Decisions

- **Self-registration stays.** `/register/` is ported, gated on the server by
  `ENABLE_ACCOUNT_REGISTRATION`.
- **Router:** React Router.
- **Styling follows the theme's variables.** The console uses the theme's own classes and layout (Keen's app
  layout, turned on with `<body>` attributes, and Bootstrap's utilities), and its own CSS, if any, reads the
  theme's CSS variables (`--bs-*`, `--bs-app-*`) instead of fixed colors and sizes, so that a theme customizes
  the console by overriding variables. Breakpoints come from `--bs-breakpoint-*`.
- **Email verification.** A password sign-up is inactive until its user follows the emailed activation
  link. Users that social sign-in creates stay inactive until an administrator activates them.

## Open questions

- Does `/api/v1/llm-clients/<id>/config/` return the same config as the workbench's `config/`?
- Does `readable_instance()` match the detail views' lookup?

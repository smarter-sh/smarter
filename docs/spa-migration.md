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
`/logout/` is gone, which closes bug 4. Next: the shell's sidebar and user menu.

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

Open question: whether `readable_instance()`, behind the resource endpoint, allows exactly what the
detail views' three-step lookup allows.

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
    (`apps/dashboard/views/views/dashboard.py:85-138`).
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
- **Email verification.** A password sign-up is inactive until its user follows the emailed activation
  link. Users that social sign-in creates stay inactive until an administrator activates them.

## Open questions

- Does `/api/v1/llm-clients/<id>/config/` return the same config as the workbench's `config/`?
- Does `readable_instance()` match the detail views' lookup?

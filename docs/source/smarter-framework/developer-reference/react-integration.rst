Django-React Integration
========================

Smarter's web console is a single-page `React <https://react.dev/>`__ application,
``@smarter/console`` (``smarter/react/packages/smarter-console``), that Django serves
(:doc:`ADR-035 </adr/035-single-page-app>`). Every console page, from the dashboard and the
resource lists to the manifest pages, the Extensions console, the manifest drop zone, the
Prompt Passthrough, the Terminal and the Prompt Engineer's Workbench, is a route of the
console. Django keeps what it is good at: authentication, sessions, CSRF protection,
permissions, url routing of the backend, static file management and deployment. React handles
everything the browser shows.

The design principle is that the console's build is an ordinary Django static asset.
`Vite.js <https://vite.dev/>`__ compiles the console into versioned JavaScript and CSS bundles
and an ``index.html``, and emits them into Django's static file hierarchy, where
``collectstatic`` picks them up like any other file. The console then talks to Django through
two apis: the :doc:`web console api <web-console-api>` under ``/api/web/``, which uses the
browser's Django session, and the public Smarter api under ``/api/v1/``.

Request Lifecycle
-----------------

The following sequence describes how a console page reaches the browser:

1. A user requests a console url, e.g. ``/workbench/llm-clients/<hashed_id>/prompt/``.
2. Django routes the request to the page's view, a subclass of
   :class:`~smarter.apps.dashboard.views.console_app.ConsoleAppView`.
3. The view answers with the console's built ``index.html``, whatever the page.
4. The browser downloads the console's scripts and styles, whose hashed names Vite wrote into
   ``index.html``.
5. The console mounts onto ``#smarter-console-root`` and loads its session from
   ``GET /api/web/session/``.
6. The console's router matches the path, and loads the page's code, a chunk of its own.
7. The page builds its component's props from the session and the route's parameters.
8. The component calls the backend's apis under ``/api/web/`` and ``/api/v1/``.

Once the console has loaded, moving between its pages doesn't ask Django for a page at all:
the router renders the next route in place, and only the apis are called.

The Single-Page Console
-----------------------

Django Serves the Console
~~~~~~~~~~~~~~~~~~~~~~~~~

Each console page keeps a Django url pattern and its url name, so that emails, settings,
templates and ``reverse()`` calls that name a page keep working. The page's view is
:class:`~smarter.apps.dashboard.views.console_app.ConsoleAppView`, or a one-line subclass of it
that exists only to keep its name, such as
:class:`~smarter.apps.prompt.views.detailviews.prompt_workbench_view.PromptWorkbenchView` or a
resource's ``<Kind>ListView``. ``ConsoleAppView`` answers ``GET`` and ``HEAD`` with the console's
``index.html``, read from ``STATIC_ROOT/react/@smarter/console/`` on each request, and:

* is never cached, so that a deployment's new build takes effect at once. The scripts and
  styles that ``index.html`` names have hashed names and are cached as other static files are.
* sets the CSRF cookie, which the console's first POST needs.
* answers 503 *The web console hasn't been built* when ``index.html`` is missing, and logs an
  error. ``make react-build`` builds and collects the console.

Because Django serves the console from its own origin, the console's requests carry the
browser's Django session cookie and CSRF token like any form post would, and no token needs to
be handed to React.

The Router and Lazy Routes
~~~~~~~~~~~~~~~~~~~~~~~~~~

The console's entry point, ``src/main.tsx``, creates a browser router from the routes in
``src/router.tsx`` and mounts the app. The sign-in, sign-up and password reset pages are routes
of their own; every other page is a child of a ``RequireAuth`` layout, which sends a visitor who
isn't signed in to the sign-in page, and draws the console's frame: the header, the sidebar and
the user menu.

Nearly every page loads lazily, with React Router's ``lazy``, so that its code is a chunk of its
own that the browser downloads the first time the page is opened. The resource lists
(``lib/lists``) and the manifest pages (``lib/manifestPages``) are tables of routes, one entry
per kind, each at the path that Django serves:

.. code-block:: tsx

  // the Prompt Engineer's Workbench, with Smarter Chat and the Console's editor, in a chunk of its own.
  {
    path: WORKBENCH_PATH,
    lazy: async () => ({ Component: (await import("@/routes/WorkbenchPage")).WorkbenchPage }),
  },

Import-Only Packages
~~~~~~~~~~~~~~~~~~~~

The React code of a page lives in a package of the npm workspace in ``smarter/react/packages``,
e.g. ``@smarter/workbench``, ``@smarter/guardrail-list`` or ``@smarter/terminal-emulator``. These
packages are *import-only*: they have no build of their own, and the console's build bundles
them. A package becomes import-only when:

* its source uses relative imports only, so that another package's build can compile it.
* ``src/index.ts`` exports its component, and the types of its props.
* its ``package.json`` points ``"main"`` and ``"exports"`` at ``./src/index.ts``, and exports
  ``./mocks``, its `MSW <https://mswjs.io/>`__ handlers, for the console's stories and tests.
* it has no ``build`` script. Its ``main.tsx``, ``index.html`` and ``vite.config.ts`` remain for
  its development page only (``npm run dev``).

The page's component receives everything it needs as props. The console's route builds them,
rather than Django rendering them into a template.

Props From the Session
~~~~~~~~~~~~~~~~~~~~~~

``GET /api/web/session/``
(:class:`~smarter.apps.api.web.session.views.ConsoleSessionView`) tells the console who is using
it and how the platform is set up: the user, their profile and account, the cookie names and
domain, the sidebar's links, the onboarding state, and the feature flags, such as
``reactDebugMode``, ``serverLogs`` or ``terminal``. Its contract is the Pydantic model
:class:`~smarter.apps.api.web.session.contract.ConsoleSession`, from which the console's
TypeScript types (``src/contract.gen.ts``) are generated. ``SessionProvider`` loads it once, when
the console starts, and pages read it with ``useConsoleSession()``.

A page turns the session into its component's props. ``lib/djangoSession.ts`` builds the
``SessionContext`` of ``@smarter/common`` that every package's api calls use, with the CSRF and
session cookie names, the cookie domain, the debug flag and a new request id. A flag that is off
hides its page: the tool pages (``routes/ToolPages``) show *Page not found* while the session's
``manifestDropZone``, ``passthrough`` or ``terminal`` is off.

An Example: The Prompt Engineer's Workbench
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The LLMClient prompt engineering workbench is a good example. It is a highly interactive
application, with streaming chat responses, live server logs, a manifest editor and complex
state, and every layer of the integration shows in it.

**Django.** A url pattern routes ``/workbench/llm-clients/<hashed_id>/prompt/`` to
:class:`~smarter.apps.prompt.views.detailviews.prompt_workbench_view.PromptWorkbenchView`, a
``ConsoleAppView``. It answers with the console's ``index.html``, like every other page, and it
needs no template and no context.

**The route.** The console's router matches ``WORKBENCH_PATH``,
``/workbench/llm-clients/:id/prompt``, and loads ``src/routes/WorkbenchPage.tsx``. The page first
asks the resource api, ``/api/web/dashboard/resource/llmclient-<hashed_id>/``, whether the user
may read the LLMClient. On a 404, for an unknown LLMClient, another account's, or a staff-only
one, it shows *Page not found*, by the same rule as the console's manifest pages.

**The configuration.** ``src/lib/workbench.ts`` builds the workbench's ``WorkbenchConfig`` from
the hashed id and the session: the chat's ``apiUrl``, the LLMClient in the public api,
``/api/v1/llm-clients/<hashed_id>/``, from whose ``config/`` the chat reads its configuration;
the Manifest, Architecture and Deployment tabs' urls in the web console api,
``/api/web/prompt/llm-clients/<hashed_id>/``; the apply, validate and delete apis; the Server Logs
stream, while the session's ``serverLogs`` is on; the cookie names; and the router's ``navigate``,
with which the workbench returns to the LLM Clients list after its LLMClient is deleted.

**The package.** ``@smarter/workbench`` renders the chat, :doc:`Smarter Chat <../smarter-chat>`
(the ``@smarter.sh/ui-chat`` npm package), and the developer Console beside it. From its own
perspective, the integration boundary is one prop: it neither knows how its code was built and
served, nor which Django view answered the url.

.. note::

   No console page references a static asset's file name, and no Django template names a
   console page's script. Vite writes the hashed names into ``index.html`` and into the chunks
   that load each other.

The Template-Tag Pattern of Django's Frame
------------------------------------------

Before the console, each page was a Django template that mounted one React app, and Django's
own frame, ``templates/dashboard/base.html``, still works this way. No console page uses it; the
next step of the migration retires it. Its widgets are React apps that the frame's templates
mount through template tags: the user menu (``@smarter/dashboard-user-menu``), the **Did you
know?** tip (``@smarter/didyouknow``), onboarding (``@smarter/onboarding``) and the welcome dialog
(``@smarter/welcome``). The console imports the same packages into its own frame, and builds
their props from the session.

.. important::

   A new page is a console page: an import-only package and a route of ``@smarter/console``,
   served by a ``ConsoleAppView``. Never add a new Django template for a page.

.. image:: https://cdn.smarter.sh/docs/smarter-framework/react-integration/react-integration.002.png
  :alt: View, Template, and React Component Integration
  :width: 100%

An Example: The User Menu
~~~~~~~~~~~~~~~~~~~~~~~~~

The frame's navbar, ``templates/dashboard/navbar.html``, includes
``templates/react/dashboard-user-menu.html``, which loads
:mod:`smarter.apps.dashboard.templatetags.react_dashboard_user_menu`. Its two tags do the work:

* ``dashboard_user_menu_react_assets`` returns the app's JavaScript and CSS files, from its
  ``manifest.json``.
* ``dashboard_user_menu`` returns the root element's attributes: the cookie names and domain,
  who the user is, their profile image, their account, the languages, and the urls of the
  menu's apis, reversed with Django's ``reverse()`` so that routing stays in Django.

The template renders the root element, with that configuration in custom HTML attributes:

.. code-block:: html

  <div
    id="smarter-dashboard-user-menu-root"
    smarter-csrf-cookie-name="csrftoken"
    smarter-django-session-cookie-name="sessionid"
    smarter-cookie-domain="platform.example.com"
    smarter-profile-image-api-url="/api/web/account/profile-image/"
    ...
  >

and the ``<link>`` and ``<script>`` elements of the app's assets:

.. code-block:: jinja

  {% dashboard_user_menu_react_assets as user_menu_assets %}
  {% for js_file in user_menu_assets.js %}
    <script class="smarter" type="module" src="{% static 'react/@smarter/dashboard-user-menu/' %}{{ js_file }}"></script>
  {% endfor %}

The package's ``main.tsx`` finds the root element, reads the attributes, builds its
``SessionContext`` and renders the app. This is what the console replaces: there, the same
configuration comes from the session api instead of from attributes.

React Build Manifest
~~~~~~~~~~~~~~~~~~~~

A widget's script names cannot be written into a template, because Vite gives every production
file a content-based hash for browser cache invalidation. Instead, the widget's build writes a
``manifest.json`` file, the authoritative list of the JavaScript and CSS files it produced, and
Django reads it at render time. Its exact contents vary with the application's dependencies,
vendor libraries and code-split modules. The following example shows the manifest of an
application that imports xterm.js:

.. code-block:: json

  {
    "_rolldown-runtime-B8sk0Y4v.js": {
      "file": "assets/rolldown-runtime-B8sk0Y4v.js",
      "name": "rolldown-runtime"
    },
    "_xterm-BVTBumqj.js": {
      "file": "assets/xterm-BVTBumqj.js",
      "name": "xterm",
      "imports": [
        "_rolldown-runtime-B8sk0Y4v.js"
      ],
      "css": [
        "assets/xterm-kHJ-D0s7.css"
      ]
    },
    "_xterm-kHJ-D0s7.css": {
      "file": "assets/xterm-kHJ-D0s7.css",
      "src": "_xterm-kHJ-D0s7.css"
    },
    "index.html": {
      "file": "assets/index-B1eOzN5c.js",
      "name": "index",
      "src": "index.html",
      "isEntry": true,
      "imports": [
        "_rolldown-runtime-B8sk0Y4v.js",
        "_xterm-BVTBumqj.js"
      ],
      "css": [
        "assets/index-58MXwt-L.css"
      ]
    },
    "_custom": {
      "buildTime": "2026-10-12T01:09:47.988Z",
      "version": "0.3.0",
      "buildEnv": "production"
    }
  }

Every entry except ``_custom`` is a chunk generated by Vite. ``_custom`` is build information
that the widgets' Vite configuration adds after the build, with its ``addCustomManifestData``
plugin: the build time, the package's version and the build's ``NODE_ENV``.

One entry, marked ``"isEntry": true``, is the application's entry point and the root of the
dependency graph. Rather than loading only the entry point's file, Django traverses the manifest
recursively to find every file the application needs: imported chunks, shared runtime modules,
vendor bundles and their CSS.

Django doesn't read the manifest as loose JSON. It validates the file against the Pydantic model
:class:`~smarter.lib.django.templatetags.smarter_react_contract.ViteManifest`: each chunk is a
:class:`~smarter.lib.django.templatetags.smarter_react_contract.ViteManifestChunk`, and
``_custom`` is a
:class:`~smarter.lib.django.templatetags.smarter_react_contract.ReactAppBuildInfo`. Chunks accept
fields that Vite or Rolldown add in newer versions, so a Vite upgrade doesn't break page
rendering. ``_custom`` is Smarter's own shape and accepts only its three fields. A manifest that
is missing, isn't JSON, or doesn't match the model is logged as an error and treated as absent,
and the page then renders without the widget's assets.

Django Template Tags
~~~~~~~~~~~~~~~~~~~~

`Custom Django template tags <https://docs.djangoproject.com/en/6.0/howto/custom-template-tags/>`__
keep the manifest's structure out of the templates. Each widget's tag module creates a
:class:`~smarter.lib.django.templatetags.smarter_react_templatetag_manager.SmarterReactTemplateTagManager`
for its package, which loads the ``manifest.json`` file, finds the entry point, collects its
dependencies, and returns a
:class:`~smarter.lib.django.templatetags.smarter_react_contract.ReactAppAssets` model with
``js`` and ``css`` attributes. The entry point's own files come first, followed by those of its
imports. The template renders a ``<script>`` or ``<link>`` element for each, with no knowledge of
how the assets were generated. This approach:

* eliminates hardcoded asset filenames.
* supports cache-safe hashed build artifacts.
* resolves code-split dependencies automatically.
* keeps manifest traversal out of templates.

See :doc:`SmarterReactTemplateTagManager <lib/django/templatetags>`, which also documents the
Pydantic models of the manifest and of the assets.

Vite Configuration
------------------

`Vite.js <https://vite.dev/>`__ compiles the React code, optimizes the bundles, and writes them
where Django serves them. Rather than requiring React code to understand deployment
environments, static asset locations or runtime integration, these concerns are centralized in
the build configuration. The console's configuration,
``smarter/react/packages/smarter-console/vite.config.ts``, addresses these requirements:

- **Static Asset Integration**
    Writes ``index.html`` and its assets into Django's static file hierarchy,
    ``smarter/static/react/@smarter/console/``, with the base url ``/static/react/@smarter/console/``,
    so that they take part in the ``collectstatic`` workflow and ``ConsoleAppView`` finds
    ``index.html`` in ``STATIC_ROOT``.
- **Hashed File Names**
    Names every script, chunk and stylesheet ``assets/[name]-[hash]``, so that browsers can cache
    them for as long as they like.
- **Code Splitting**
    Writes each lazy route, and the import-only packages it uses, into a chunk of its own.
- **Development Proxying**
    Serves the console at ``http://localhost:5173/`` with ``npm run dev``, and proxies every path
    that belongs to the backend (``/api``, ``/admin``, ``/social-auth``, ``/i18n``, ``/jsi18n``,
    ``/static`` and the ``/ws`` WebSocket) to the Django dev server at ``http://localhost:9357``, so
    that the browser sees one origin and Django's session and CSRF cookies work as they do in
    production.
- **Production Hardening**
    Removes ``console.debug()`` calls from production builds, with the Oxc minifier, so that
    debugging output can't disclose sensitive information.

.. code-block:: typescript

  export default defineConfig(({ command }: ConfigEnv) => ({
    plugins: [react()],
    base: command === "serve" ? "/" : `/static/react/${packageName}/`,
    resolve: {
      alias: {
        "@": path.resolve(import.meta.dirname, "./src"),
      },
    },
    build: {
      manifest: "manifest.json",
      outDir: `../../../smarter/static/react/${packageName}`,
      emptyOutDir: true,
      rolldownOptions: {
        output: {
          entryFileNames: "assets/[name]-[hash].js",
          chunkFileNames: "assets/[name]-[hash].js",
          assetFileNames: "assets/[name]-[hash][extname]",
          // The Oxc minifier's way of removing console.debug() calls, which can log sensitive data.
          minify: {
            compress: {
              treeshake: {
                manualPureFunctions: ["console.debug"],
              },
            },
          },
        },
      },
    },
    server: {
      port: 5173,
      strictPort: true,
      proxy: backendProxy(),
    },
  }));

An import-only package's ``vite.config.ts``, such as
``smarter/react/packages/smarter-workbench/vite.config.ts``, is for its development page only: it
has no ``build`` section, and proxies ``/api`` and ``/static`` to the Django dev server. The frame
widgets' configurations also write a ``manifest.json`` with the ``_custom`` build information
that Django's template tags validate.

Build, Deployment, and CI/CD Considerations
-------------------------------------------

The React code is a single npm workspace, ``smarter/react``, with one package per page or
widget. ``npm run build`` in the workspace builds, in order, the libraries that others import
(``@smarter/common``, ``@smarter/didyouknow``'s and ``@smarter/onboarding``'s libraries,
``@smarter.sh/ui-widgets`` and ``@smarter.sh/ui-chat``), then every package that has a ``build``
script: the console, which bundles every page package, and the frame's widgets, each into its
own folder of Django's static file hierarchy, such as:

.. code-block:: text

  static/react/@smarter/console/
  static/react/@smarter/dashboard-user-menu/

.. note::

  React build artifacts are treated as ordinary Django static assets.

  From Django's perspective, compiled React bundles are no different from any other static
  resource such as CSS, images, or JavaScript files. Once generated, they participate in the
  standard Django static asset workflow, including collectstatic, static file serving, and cache
  management.

  Because React assets are generated before Django is deployed, the frontend build remains
  cleanly separated from the Django runtime. React code can be developed, versioned, tested, and
  rebuilt independently while still integrating into Django's deployment pipeline.

CORS
~~~~

``@smarter/common`` sends a set of custom HTTP headers with every api request (see
``smarter/react/packages/smarter-common/src/lib/django.tsx``). They are listed in
``CORS_ALLOW_HEADERS`` in ``smarter.settings.base``, so that a cross-origin request, e.g. from the
embedded Smarter Chat, may carry them. CORS is switch-enabled: the ``enable_middleware_cors``
waffle switch must be on for a React app on another origin to call the backend.

.. code-block:: typescript

  const requestHeaders = {
    Accept: applicationJson,
    "X-CSRFToken": csrftokenValue!,
    "Content-Type": applicationJson,
    "X-Smarter-Client": sessionContext.smarterClient,
    "X-Smarter-ClientVersion": sessionContext.smarterClientVersion,
    "X-Smarter-ClientType": "react",
    "X-Smarter-RequestId": sessionContext.smarterRequestId,
    "X-Smarter-Capabilities": capabilities,
  };

Operational Considerations
~~~~~~~~~~~~~~~~~~~~~~~~~~

* Source Control Exclusion
    Compiled React build artifacts are intentionally excluded from the Git repository and are
    never committed to source control. Build outputs are ephemeral deployment artifacts and are
    regenerated as part of the build process.
* Build Prerequisites
    Django can serve no console page until the console has been built and collected: until then
    every page answers 503. The frame's template tags, likewise, depend on their widgets'
    ``manifest.json``. Keep this in mind when, for example, you are changing versions in
    ``package.json``.
* Rebuilding After React Changes
    Use ``make react-build``, which builds the workspace, runs ``collectstatic`` and rebuilds the
    Docker image, rather than ``make build`` alone, which uses the static files collected earlier.
* CI/CD Pipeline Initialization
    GitHub Actions workflows begin with a clean checkout that contains no compiled frontend
    assets. Accordingly, the React build (the ``react-build`` action of ``build.yml``, which
    restores the build from a cache when the React source is unchanged) runs early, before
    Docker builds, collectstatic, integration tests, or deployment stages that depend on it.
* Static File Synchronization
    During local development, be aware of the distinction between Vite's development server,
    Django's static asset directories, and the Django staticfiles runtime directory. Stale build
    artifacts can lead to confusing runtime behavior if these become out of sync.
* Container Build Dependencies
    Docker images that serve the console must be built only after the frontend build has
    completed, so that ``index.html``, the compiled bundles and the widgets' ``manifest.json``
    files are inside the image at runtime.
* Published Packages
    :doc:`Smarter Chat <../smarter-chat>`, the chat of the Prompt Engineer's Workbench, is also
    published to npm, as ``@smarter.sh/ui-chat``, and so is ``@smarter.sh/ui-widgets``. Both are
    packages of the workspace (``smarter/react/packages/smarter.sh-chat`` and
    ``smarter/react/packages/smarter.sh-widgets``) that build on their own, as libraries that the
    console's pages import, and GitHub Actions publishes them with each Smarter release, under the
    platform's version (``uiChatRelease.yml`` and ``uiWidgetsRelease.yml``).
* Convenience Tooling
    ``make react-build`` and ``make react-build-ci`` simplify the common frontend workflows and
    keep Django's static directories aligned with the current React build.

Collectively, these conventions give a predictable, reproducible deployment model that works
the same way in local development, CI/CD workflows, Docker image builds and production. The
result keeps the operational simplicity of a Django deployment while the web console is a
modern single-page application.

.. toctree::
  :maxdepth: 1
  :caption: Technical Reference

  react-integration/dashboard
  react-integration/dashboard-user-menu
  react-integration/didyouknow
  react-integration/doodle
  react-integration/onboarding
  react-integration/llmclient-list
  react-integration/manifest-dropzone
  react-integration/prompt-passthrough
  react-integration/smarter-chat
  react-integration/terminal-application
  react-integration/welcome
  lib/django/templatetags

.. toctree::
  :maxdepth: 1
  :caption: Code Samples

  react-integration/example-vite
  react-integration/example-template-tag
  react-integration/example-template
  react-integration/example-view
  react-integration/example-react-mount

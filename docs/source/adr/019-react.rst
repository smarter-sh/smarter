ADR-019: React
==============


Status
------
Accepted

Context
-------
JavaScript front-end frameworks can add complexity to build, deployment, and
maintenance, and Django's built-in templating tools remain a simpler and more
maintainable approach for static or form-driven pages. Many parts of the web
console, however, need interactivity that server-rendered templates cannot
provide: streaming log output, drag-and-drop manifest uploads, live prompt
editing, chat, and resource list pages with inline clone, rename and delete.

The risk of adopting React is that it turns into a separate single-page
application with its own routing, authentication, configuration and deployment
pipeline, duplicating what Django already does well. Smarter avoids that risk
with a single, documented integration pattern in which React build artifacts
are ordinary Django static assets.

Decision
--------
React is fully supported anywhere in the Smarter web console. Any console page
may be implemented as a React application, provided it follows the integration
pattern described in :doc:`Django-React Integration
</smarter-framework/developer-reference/react-integration>`:

- **Django owns the page.** A Django URL and view serve every page. The view
  selects the template, generates runtime configuration (API endpoints via
  ``reverse()``, cookie names, cookie domain) and passes it as template context.
  React does not do client-side routing between console pages.
- **The template hosts the app.** The template renders a mounting element whose
  custom ``smarter-*`` HTML attributes carry the runtime configuration, and uses
  Smarter's React template tags to inject the app's ``<script>`` and ``<link>``
  elements.
- **Vite builds into Django's static files.** Each React app is a package in the
  npm workspace in ``smarter/react/packages``, built by Vite into
  ``static/react/<package>/`` with a ``manifest.json``. Django discovers the
  hashed asset filenames by traversing that manifest, which is validated against
  a Pydantic model. Templates and React code never reference asset filenames
  directly.
- **Shared code lives in** ``@smarter/common``. Session context, authenticated
  API requests (``fetchDjangoUrl``) and the Smarter request headers come from
  this package rather than being reimplemented per app.
- **React apps are tested and linted in CI.** Each package follows the
  workspace's Storybook, Vitest, ESLint and Prettier conventions, and runs in the
  ``react`` job of ``.github/workflows/test.yml``.

Django templates remain the default for pages that don't need client-side
interactivity. Contributors should choose React when a page's behavior
justifies it, not by default.

Alternatives Considered
-----------------------
- Limiting React to a single area of the platform (the original form of this
  ADR, which confined it to the Prompt Engineer Workbench).
- Running React as a standalone single-page application with its own routing,
  authentication and deployment, communicating with Django only through APIs.
- Using Django templates exclusively for all UI.

Consequences
------------
- **Positive:**

  - Interactive features can be built anywhere in the console with a modern
    component framework.
  - Django keeps authentication, sessions, CSRF protection, routing and
    deployment, so React apps inherit them without additional code.
  - Every React app integrates the same way, so a new app can be modeled on an
    existing one (for example the resource list pages) and contributors learn
    the pattern once.
  - React builds participate in ``collectstatic`` and the normal Docker build,
    so there is no separate front-end deployment.
  - Frontend and backend work can proceed largely independently across a narrow,
    well-defined boundary of HTML attributes and API endpoints.

- **Negative:**

  - Contributors need Node.js, npm and Vite in addition to the Python toolchain.
  - React changes require an npm build and ``collectstatic`` before Django can
    serve them, and a page whose ``manifest.json`` is missing renders without
    its React app.
  - The project maintains two test and lint toolchains, one for Python and one
    for the npm workspace.

Related ADRs
------------
- :doc:`ADR-000: Introduction <000-intro>`
- :doc:`ADR-001: Django <001-django>`
- :doc:`ADR-025: Django Templates <025-templates>`
- :doc:`ADR-031: Pydantic Models Over Raw JSON <031-pydantic-over-json>`

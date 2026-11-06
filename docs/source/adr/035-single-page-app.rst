ADR-035: The Web Console as a Single-Page App
=============================================

Status
------
Proposed. When accepted, it supersedes :doc:`ADR-019 <019-react>`'s rule that Django owns every
console page.

Context
-------
Under :doc:`ADR-019 <019-react>`, every console page is a Django view and template, and React apps
are widgets mounted inside them. :doc:`ADR-034 <034-web-console-api>` moved the JSON endpoints those
widgets call under ``/api/web/``, so the backend's boundary is now one prefix. What still ties the
console to Django is the page itself:

- **The frame.** Six context processors query the database or read settings on every page to render
  the header, sidebar, user menu and footer, and to pass branding and feature flags.
- **Data in the HTML.** Template tags pass each React app its configuration in ``smarter-*``
  attributes, and some pages embed data the server fetched, such as a manifest's YAML.
- **Form pages.** Sign-in, sign-up, password reset and activation are Django forms whose POST handlers
  validate, send email, create the session and redirect. Their pages host the Doodle React app, but
  the forms are server-rendered.
- **One build.** Each of about 30 React packages is built into Django's static files, and a template
  tag finds its assets through its Vite ``manifest.json``.

The project wants the console and the backend in separate repositories, released independently and
meeting only over HTTP. That is not possible while Django renders the console's pages.

Decision
--------
The web console becomes a single-page app (SPA), and Django serves only the backend.

1. **One app.** The SPA is one Vite package, ``@smarter/console`` in
   ``smarter/react/packages/smarter-console``, routed by React Router. The existing page packages
   become its routes and are imported as libraries, not mounted into templates. ``@smarter/common``
   stays the shared library. ``@smarter.sh/ui-chat`` and ``@smarter.sh/ui-widgets`` stay separately
   published packages, and ``@smarter/llmclient-deployment`` keeps its standalone bundle for the page
   a deployed LLMClient's host serves.
2. **What stays on the backend.** ``/api/v1/``, ``/api/web/``, Django admin, social sign-in
   (``/social-auth/``), deployed LLMClient hosts and custom domains, the terminal's WebSocket, email
   templates and their rendering, the unsubscribe link (mail providers POST to it without a session),
   health checks, and the translation catalogs.
3. **A startup endpoint.** ``GET /api/web/session/`` replaces the context processors and the template
   tags' data. Anonymous callers get what the sign-in pages need: branding, sign-in options and the
   switches those pages read. Signed-in callers also get the user, account, selected profile, feature
   flags, languages, onboarding and welcome state, and badge counts. It sets the CSRF cookie.
4. **The porting rule.** For each page:

   - data a template shows from the database or settings becomes JSON under ``/api/web/``;
   - what a form's POST handler does becomes a JSON action under ``/api/web/``, returning success or
     field errors, and the redirect decision moves into the SPA's router;
   - URLs, cookie names, element ids and other constants become frontend code.

   Pages that share a shape share one route. The resource list pages become one generic list route,
   and the manifest detail pages become one generic detail route, each configured per kind.
5. **The contract.** Every ``/api/web/`` response the SPA reads is a Pydantic model with a published
   JSON Schema and generated TypeScript types (:doc:`ADR-031 <031-pydantic-over-json>`), as the
   dashboard's and Smarter Chat's already are. The repository split then hands the frontend a
   contract, not shared code.
6. **Sign-in keeps Django's session.** The SPA signs in through ``/api/web/account/`` endpoints that
   create the same session cookie Django uses today. Social sign-in stays a backend redirect flow
   that ends in the SPA. Links in emails already sent keep working: ``/password-reset-link/...`` and
   ``/account/activate/...`` become SPA routes at the same paths. There are no API tokens for the
   console.
7. **Page by page, on one origin.** Until the last page moves, the SPA is served by the platform host
   it replaces. Django answers each migrated path with the SPA's built ``index.html``, and the change
   that migrates a page deletes its view, template, template tag and their tests. Django pages and
   SPA pages share the session cookie, so navigating between them just works. In development, the
   Vite dev server proxies the backend's paths to ``localhost:9357``, so the browser sees one origin
   there too.
8. **Separate hosts last.** Once no console page is left in Django, the backend moves to
   ``api.<platform>`` and the SPA becomes static files on a CDN at the platform host. That step
   brings a cookie domain both hosts share, trusted CSRF origins, CORS with credentials, and host
   routing for the api host. Then the repository splits.
9. **Fix, don't port.** A page is ported for what it should do. Dead pages are deleted, not ported.
   Ported endpoints fix the known problems of the views they replace: one generic sign-in error,
   registration gated by its switch on the server, no side effects on GET, and rate limits on
   password reset.

Alternatives Considered
-----------------------
- **Keep ADR-019.** The least work, but the console can't leave the backend's repository.
- **A separate Django console.** A thin Django project that renders the same templates from API
  calls. Every page view and context processor needs the same API work as the SPA, and the result
  still couples releases through server-side rendering.
- **Rewrite the console all at once.** Freezes console work until it ships, and ships every risk at
  once.
- **Token authentication for the console.** The SPA and the backend share a site, so session cookies
  keep working across hosts. Tokens in the browser would need a new security design for no gain.

Consequences
------------
- **Positive:**

  - The console and the backend meet only over HTTP, so they can live in separate repositories and
    release independently.
  - One router, one app shell and one build replace about 30 templates, 30 template tags and 30
    separately built bundles. The near-identical list and detail pages become one route each.
  - Navigating between console pages no longer reloads the page.
  - Every console response has a published schema, so drift between the two halves fails a test.

- **Negative:**

  - About fifteen new ``/api/web/`` endpoints, mostly for sign-in, password reset and profiles,
    where the form views' validation, emails and redirects must be rebuilt as JSON actions.
  - Strings in the frame templates move from Django's translation domain to the React one.
  - While the move is under way, the console is half Django and half SPA, and a contributor must
    know which half a page is in.
  - The final move to separate hosts changes cookie, CSRF, CORS and ingress configuration in this
    repository and in smarter-infrastructure.

Related ADRs
------------
- :doc:`ADR-019: React <019-react>`
- :doc:`ADR-021: Internationalization <021-internationalization>`
- :doc:`ADR-025: Django Templates <025-templates>`
- :doc:`ADR-031: Pydantic Models Over Raw JSON <031-pydantic-over-json>`
- :doc:`ADR-033: DRY <033-dry>`
- :doc:`ADR-034: The Web Console Api <034-web-console-api>`

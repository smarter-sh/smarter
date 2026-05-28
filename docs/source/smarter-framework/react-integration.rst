Django-React Integration
==========================

Smarter’s React integration architecture provides a highly optimized, production-grade bridge
between Django’s server-rendered web platform and modern React-based user interfaces. Rather
than treating React as a disconnected single-page application bolted onto Django, Smarter
implements React as a first-class extension of the Django runtime itself. The result is a
clean, scalable, and operationally efficient integration strategy that preserves Django’s
strengths in authentication, session management, template rendering, routing, and
industrial-grade server-side orchestration while simultaneously enabling the development of
rich, highly interactive React applications.

A central design goal of Smarter’s integration model is the complete separation of frontend
component development from backend deployment concerns. React developers are free to build
components using standard modern tooling, while Django transparently assumes responsibility
for runtime asset discovery, manifest analysis, dependency resolution, template injection,
configuration propagation, and environment-specific hosting concerns. This dramatically reduces
integration complexity inside React components and creates a reusable deployment architecture
that scales consistently across the platform.

At the core of this approach is a sophisticated runtime asset pipeline built around
`Vite.js <https://vite.dev/>`__
manifest.json build artifact. Smarter uses custom Django template tags to recursively
analyze the manifest at render time, automatically discovering all required JavaScript and CSS
dependencies — including hashed assets, shared chunks, vendor bundles, and code-split modules —
and injecting the correct <script> and <link> elements into the Django template.
Because the integration is manifest-driven, React builds remain fully cache-safe, CDN-compatible,
and environment-agnostic without requiring hardcoded filenames or manual template maintenance.

Smarter’s Vite configuration further extends this architecture by tightly aligning React’s
development and production environments with Django’s runtime behavior. Build assets are emitted
directly into Django’s static file infrastructure, development proxies transparently route API
traffic to Django, production builds automatically strip debugging statements, and optional
CloudFront deployment workflows support globally distributed CDN hosting. The system also
supports hot module replacement for an efficient frontend developer experience while preserving
full compatibility with Django’s authentication, CSRF and other middleware protection mechanisms.

The integration boundary between Django and React is intentionally lightweight and elegant.
Django templates provide stable DOM mounting points for React applications and serialize
server-side runtime context into custom HTML attributes. During initialization, React reads
these attributes and converts them into component props, allowing backend-generated context —
including API endpoints, session metadata, CSRF configuration, feature flags, and runtime
settings — to flow naturally into the frontend without additional bootstrap APIs or inline
JavaScript payloads.

Importantly, the Django view layer remains deliberately thin throughout this process. Views
focus primarily on authentication, routing, template selection, and generation of runtime
configuration context. Complex frontend integration concerns are abstracted into reusable
template tags and Vite build conventions, resulting in a clean separation of responsibilities
between backend orchestration and frontend presentation.

Collectively, these mechanisms form a generalized React integration framework that enables
Smarter to rapidly deploy sophisticated React-driven functionality throughout the platform
while maintaining operational consistency, strong security guarantees, predictable deployment
behavior, and exceptionally low integration overhead.


An Example: The Terminal Application Component
------------------------------------------------

Lets tie the pieces together with a concrete example that illustrates:
manifest analysis, Vite configuration, custom Django template tags, template mounting
strategies, and server-side context propagation. These five elements work in
concert to bring dazzling React-based functionality into the Smarter web console.

Smarter's live view of server log activity is a great example, in that it is a highly
interactive React component that involves live streaming data, complex state management,
and tight integration with Django's authentication and server-side context management.
Functionality of this nature could only be implemented in a frontend framework like React.

.. image:: https://cdn.smarter.sh/docs/smarter-framework/react-integration/terminal-emulator-react-component.png
  :alt: View, Template, and React Component Integration
  :width: 100%


React Build Manifest
----------------------

The React build's manifest.json build artifact is generated by Vite.js
(hereon, Vite) and provides a single
source of truth for the names and locations of all JavaScript and CSS build assets.
It is important to recognize that the contents of a manifest.json file can vary
widely depending on the extent to which it combines other 3rd party modules and
assets. Moreover, the individual asset filenames are hashed and thus are necessarily
indeterminate in order to prevent browser caching issues.

Following is an example manifest.json file for the Terminal Application:

.. code-block:: json

  {
    "_rolldown-runtime-B3igc2qu.js": {
      "file": "assets/rolldown-runtime-B3igc2qu.js",
      "name": "rolldown-runtime"
    },
    "_xterm-D5XSfLrr.js": {
      "file": "assets/xterm-D5XSfLrr.js",
      "name": "xterm",
      "imports": [
        "_rolldown-runtime-B3igc2qu.js"
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
      "file": "assets/index-CZK_Bxxh.js",
      "name": "index",
      "src": "index.html",
      "isEntry": true,
      "imports": [
        "_rolldown-runtime-B3igc2qu.js",
        "_xterm-D5XSfLrr.js"
      ],
      "css": [
        "assets/index-58MXwt-L.css"
      ]
  }

One and only one top-level key will contain a dict with an "isEntry" key set to true.
This is the entry point for the React component, and the objects which should be
recursively analyzed to determine the complete set of build assets to add to the
Django template. Analysis of this nature is handled by custom Django template tags (see below).

Vite Configuration
--------------------

The manifest.json file is generated by `Vite.js <https://vite.dev/>`__,
and its structure and contents are determined entirely by the Vite build
configuration. Vite is a high-performance frontend build system that Smarter
uses to compile, optimize, and package React applications for integration into
the Django web console.

Smarter’s Vite configuration serves as a critical integration layer between
the React frontend and the Django backend. Rather than embedding deployment
logic directly into React applications, Smarter centralizes these concerns
inside the build pipeline itself. This creates a clean separation of concerns
that allows React components to be developed largely independently from the
details of how assets are hosted, versioned, discovered, and injected into
Django templates at runtime.

Integrating React into a server-rendered Django platform introduces several
architectural and operational challenges, including:

- **Manifest Generation**
    Producing a manifest.json file containing
    hashed asset filenames that serve as the authoritative source of truth for
    all JavaScript, CSS, and chunk dependencies generated during the build.
- **Development Proxying**
    Configuring proxy routes so that API requests
    originating from the Vite development server are transparently forwarded
    to the Django backend instead of the frontend development server.
- **Static Asset Integration**
    Building React assets directly into Django’s
    static file hierarchy so that compiled frontend resources participate in
    Django’s collectstatic workflow and are served consistently alongside
    the rest of the platform.
- **Security Compatibility**
    Preserving compatibility with Django’s
    authentication, CSRF protection, session cookies, and same-origin security
    model by avoiding unnecessary cross-origin frontend deployments.
- **CDN Deployment**
    Optionally synchronizing production build artifacts
    to a public AWS CloudFront distribution backed by S3 for globally distributed,
    low-latency asset delivery.
- **Production Hardening**
    Removing console.debug() statements from
    production bundles in order to reduce unnecessary console noise and avoid
    leaking potentially sensitive runtime information.
- **Caching Optimization**
    Splitting large third-party dependencies such
    as xterm.js into isolated bundles so that vendor assets can remain
    browser-cached independently from frequently changing application code.
- **Developer Experience**
    Supporting hot module replacement (HMR) and
    rapid incremental rebuilds to provide a fast and efficient React development
    workflow without compromising Django runtime compatibility.

The following example illustrates the Vite configuration used by the Terminal
Application component.

.. code-block:: javascript

  const postBuildPlugin: PluginOption = {
    name: "post-build",

    closeBundle() {
      if (packageJson.config.cdnDeploy === true) {
        execSync(
          `aws s3 sync ../../smarter/static/react/${packageName} ${packageJson.config.s3BucketPath} --acl public-read --delete`,
          { stdio: "inherit" },
        );
        execSync(
          `aws --no-cli-pager cloudfront create-invalidation --distribution-id ${packageJson.config.cloudfrontDistributionId} --paths '/react/${packageName}/*'`,
          { stdio: "inherit" },
        );
      }
    },
  };

  export default defineConfig(({ command }: ConfigEnv) => ({
    plugins: [
      react(),
      postBuildPlugin,
    ],
    // We use esbuild to remove console.debug statements in production builds
    // in order to avoid leaking potentially sensitive information in
    // production environments.
    esbuild: {
      pure: ["console.debug"],
    },
    // Builds are also saved into the Django static directory so that these
    // files can be included in the Django collectstatic process and served by
    // Django at runtime in local development environments. For development
    // we need to be able to support serving these files both from the Vite
    // dev server as well as the Django dev server. We set the base to '/'
    // so that Vite's dev server can serve these files. Separately, we persist
    // the actual build files to the Django static directory and set up a proxy
    // in the Vite dev server to forward requests to the Django dev server.
    base: command === "serve" ? "/" : `/static/react/${packageName}/`,
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
    build: {
      minify: "esbuild" as const,
      // ------------------------------------------------------------------------
      // The manifest is needed for hosting builds from Django (both dev and prod).
      // It is used by Django templatetags to determine the correct file names to include
      // in the HTML template. This is necessary because Vite includes a
      // hash in the file names for cache busting.
      // ------------------------------------------------------------------------
      manifest: "manifest.json",
      // ------------------------------------------------------------------------
      // we're placing our build output in the primary Django static directory so
      // that these files are automatically included in the Django collectstatic
      // process and served by Django at runtime.
      //
      // In development, we rely on Vite's dev server to serve these files, so we
      // set the outDir to a directory that is not used by the Django dev server.
      // ------------------------------------------------------------------------
      outDir: `../../smarter/static/react/${packageName}`,
      emptyOutDir: true,
      // ------------------------------------------------------------------------
      // We want to bundle xterm.js and its addons separately from the rest of the
      // application code in order to optimize caching. This way, if we make changes
      // to our application code, the xterm.js bundle can still be cached by the
      // browser and won't need to be re-downloaded.
      // ------------------------------------------------------------------------
      rollupOptions: {
        output: {
          entryFileNames: "assets/[name]-[hash].js",
          chunkFileNames: "assets/[name]-[hash].js",
          assetFileNames: "assets/[name]-[hash][extname]",
          manualChunks(id: string) {
            if (id.includes("node_modules/xterm") || id.includes("node_modules/@xterm")) {
              return "xterm";
            }
            return undefined;
          },
        },
      },
    },
    // Django collects static files and serves them from /static/
    // We need to create proxy servers in React's dev environment
    // so that these requests are served from the Django dev server instead
    // of the React dev server.
    //
    // Most of these cases stem from <link> elements added to this index.html
    // containing platform-wide stylesheets and scripts that originate from
    // and are served by the Django dev server. These are added to index.html
    // in order to keep this React dev environment as close to the runtime
    // environment as possible.
    server: {
      proxy: {
        "/api": "http://localhost:9357",
        "/assets": {
          target: "http://localhost:9357", // Django dev server
          changeOrigin: true,
          rewrite: (path: string) => `/static${path}`,
        },
        "/common-styles.css": {
          target: "http://localhost:9357",
          changeOrigin: true,
          rewrite: (path: string) => `/static${path}`,
        },
        "/dashboard/": "http://localhost:9357",
        [`/static/react/${packageName}/`]: {
          target: "http://localhost:5173",
          changeOrigin: true,
          rewrite: (path: string) => path.replace(new RegExp(`^/static/react/${packageName}/`), "/"),
        },
        "/static": {
          target: "http://localhost:9357",
          changeOrigin: true,
        },
        "/workbench/": "http://localhost:9357",
      },
    },
  }));


Django Template Tags
----------------------

Django template tags are a server-side extensibility mechanism that allows
developers to embed executable Python-backed logic directly into Django templates
using a declarative syntax such as ``{% tag_name %}``. Custom template tags are
especially useful for dynamically processing a React manifest.json file generated
by modern frontend build tools like Vite or Webpack, because the manifest provides
a machine-readable mapping between original source entry points and their versioned
production assets. A Django template tag can load and parse the manifest at render
time, identify the correct JavaScript and CSS bundles associated with a specific
React entry point, and automatically inject the appropriate <script> and <link>
elements into the HTML template. This approach eliminates hardcoded asset filenames,
enables cache busting through hashed asset names, supports code splitting and
lazy-loaded chunks, and creates a clean integration layer between Django’s
server-rendered templates and React’s compiled frontend assets.

Following is an example of how Smarter's custom template tags are used as an
iterator that generates the CSS and JS asset paths and filenames for the Terminal
App React component. Effectively, the custom template tag code logic provides
a clean interface for the Django template to interact with the manifest.json
file, abstracting away the details of how to recursively parse the manifest and
generate the correct asset paths and filenames.

.. code-block:: jinja

  {% block style_extra %}
    {{ block.super }}

    {% terminal_emulator_react_assets as assets %}
    {% for css_file in assets.css %}
      <link class="smarter" rel="stylesheet" href="{% static 'react/terminal_emulator/' %}{{ css_file }}">
    {% endfor %}
  {% endblock %}

.. code-block:: jinja

  {% block javascript_extra %}
    {{ block.super }}

    {% terminal_emulator_react_assets as assets %}
    {% for js_file in assets.js %}
      <script class="smarter" type="module" src="{% static 'react/terminal_emulator/' %}{{ js_file }}"></script>
    {% endfor %}
  {% endblock %}

See this :doc:`custom Django Template Tag <react-integration/example-template-tag>`
implementation for the Terminal App React component.

Django Template
-------------------

The Django template is primarily responsible for providing a DOM entry point for the React
component to mount to. It is secondarily responsible for mapping Django view context to
custom HTML attributes on the DOM element that serves as the mounting point for the React
component. These custom attributes function as a transport layer for React props, allowing
server-side Django context data to be passed into the client-side React application during
React component initialization.

When the React application boots, it locates the mounting element in the DOM and reads these
attributes using standard browser APIs such as Element.getAttribute() or HTMLElement.dataset.
The extracted values are then transformed into React props and supplied to the root component.
This pattern provides a lightweight integration boundary between Django and React without requiring
inline JavaScript bootstrapping or additional API calls during initial page load. This all
happens lightning fast.

This context information typically includes salient cookie names for Django session management,
CSRF protection, authenticated API communication, feature flags, endpoint URLs, and any other
configuration values required by the React component at runtime.

.. code-block:: html

  <div
    id="smarter-terminal-emulator-root"
    smarter-api-path="/dashboard/logs/api/stream/"
    smarter-cookie-domain="alpha.platform.example.com"
    smarter-csrf-cookie-name="csrftoken"
    smarter-django-session-cookie-name="sessionid"
  >


Django View
-------------

The Django view is responsible for mapping the URL endpoint to the Django HTML template and
for generating the server-side context consumed by that template. In this architecture, the
view layer is intentionally kept thin and focused primarily on request orchestration, template
selection, authentication, and serialization of runtime configuration values required by the
React frontend.

The view assembles a context dictionary containing configuration and integration metadata,
including cookie names, CSRF settings, API endpoints, and DOM identifiers. These values are
subsequently rendered into custom HTML attributes by the Django template, where they become
available to the React application as initialization props during the client-side bootstrap
process.

A live example of a Django view that serves the dashboard template:

.. code-block:: python

  class TerminalEmulatorLogView(SmarterAuthenticatedNeverCachedWebView):

      def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:

          context = {
              "terminal": {
                  "root_id": "smarter-terminal-emulator-root",
                  "csrf_cookie_name": settings.CSRF_COOKIE_NAME,  # this is the CSRF token cookie that should be included in the header of the POST request from the frontend.
                  "django_session_cookie_name": settings.SESSION_COOKIE_NAME,  # this is the Django session.
                  "cookie_domain": settings.SESSION_COOKIE_DOMAIN,
                  "api_url": "/path/to/log/stream/",  # the WebSocket endpoint with the log data stream.
              }
          }
          self.template_path = "react/terminal-emulator.html"

          return render(request, self.template_path, context=context)

.. image:: https://cdn.smarter.sh/docs/smarter-framework/react-integration/view-template-integration1.png
  :alt: View, Template, and React Component Integration
  :width: 100%




.. toctree::
  :maxdepth: 1
  :caption: Technical Reference

  react-integration/dashboard
  react-integration/prompt-list
  react-integration/terminal-application
  react-integration/prompt-passthrough
  react-integration/smarter-chat

.. toctree::
  :maxdepth: 1
  :caption: Code Samples

  react-integration/example-vite
  react-integration/example-template-tag
  react-integration/example-template
  react-integration/example-view
  react-integration/example-react-mount

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

.. image:: https://cdn.smarter.sh/docs/smarter-framework/react-integration/react-integration.002.png
  :alt: View, Template, and React Component Integration
  :width: 100%

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

.. image:: https://cdn.smarter.sh/docs/smarter-framework/react-integration/react-integration.001.png
  :alt: View, Template, and React Component Integration
  :width: 100%


Django Objects
----------------

Lets begin with familiar territory, the Django url, view and template. The url path
is responsible for routing incoming requests to the correct view.

In this example, we're leveraging Django's reverse() function to define the URL
for the React component's API endpoint based on defining Django 'namespaces'.
This allows us to avoid hardcoding URLs in the Django template and React component,
and instead rely on Django's URL routing system to generate the correct URLs at runtime.

.. image:: https://cdn.smarter.sh/docs/smarter-framework/react-integration/react-integration.003.png
  :alt: View, Template, and React Component Integration
  :width: 100%

The view is responsible for selecting the correct template and generating
the context required to render that template. And the template is responsible
for rendering the HTML and providing a DOM entry point for the React
component to mount to.

.. image:: https://cdn.smarter.sh/docs/smarter-framework/react-integration/react-integration.004.png
  :alt: View, Template, and React Component Integration
  :width: 100%

The template renders custom HTML attributes calculated in the view onto the DOM
element that serves as the mounting point for the React component. It also leverages
a custom Django template tag to parse the manifest.json file generated by the React build
and to inject the correct <script> and <link> elements for the React component's
JavaScript and CSS assets (highlighted in green and further explained below).

.. image:: https://cdn.smarter.sh/docs/smarter-framework/react-integration/react-integration.005.png
  :alt: View, Template, and React Component Integration
  :width: 100%

The React component itself is responsible for rendering the user interface,
managing component state, and orchestrating interactions with the Django
backend via API calls to the endpoint defined in the view and passed through
the template as a custom HTML attribute. The React component is completely
agnostic to the details of how the asset pipeline works, how the manifest
is structured, and how the assets are injected into the DOM. This is a critical point.
The React component is entirely focused on frontend behavior and presentation logic,
while Django and the build pipeline handle all of the deployment, hosting, and integration concerns.

.. image:: https://cdn.smarter.sh/docs/smarter-framework/react-integration/react-integration.006.png
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
    }
  }

One and only one top-level key will contain a dict with an "isEntry" key set to true.
This is the entry point for the React component, and the objects which should be
recursively analyzed to determine the complete set of build assets to add to the
Django template. Analysis of this nature is handled by custom Django template tags (see below).

.. image:: https://cdn.smarter.sh/docs/smarter-framework/react-integration/react-integration.007.png
  :alt: View, Template, and React Component Integration
  :width: 100%


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
          `aws s3 sync ../../../smarter/static/react/${packageName} ${packageJson.config.s3BucketPath} --acl public-read --delete`,
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
      outDir: `../../../smarter/static/react/${packageName}`,
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
      <link class="smarter" rel="stylesheet" href="{% static 'react/@smarter/terminal-emulator/' %}{{ css_file }}">
    {% endfor %}
  {% endblock %}

.. code-block:: jinja

  {% block javascript_extra %}
    {{ block.super }}

    {% terminal_emulator_react_assets as assets %}
    {% for js_file in assets.js %}
      <script class="smarter" type="module" src="{% static 'react/@smarter/terminal-emulator/' %}{{ js_file }}"></script>
    {% endfor %}
  {% endblock %}

See :doc:`SmarterReactTemplateTagManager <lib/django/templatetags>`.

.. image:: https://cdn.smarter.sh/docs/smarter-framework/react-integration/react-integration.008.png
  :alt: View, Template, and React Component Integration
  :width: 100%

.. image:: https://cdn.smarter.sh/docs/smarter-framework/react-integration/react-integration.010.png
  :alt: View, Template, and React Component Integration
  :width: 100%


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

The Django template is also responsible for invoking custom template tags that
analyze the React build's manifest.json file and inject the correct <script>
and <link> elements for the React component's JavaScript and CSS assets.

.. image:: https://cdn.smarter.sh/docs/smarter-framework/react-integration/react-integration.009.png
  :alt: View, Template, and React Component Integration
  :width: 100%


Build-Deploy and CI-CD Considerations
---------------------------------------

React apps are organized and built as a single npm workspace containing
multiple packages, each of which is otherwise completely independent,
producing its own manifest.json file and associated build assets. Each
package is responsible for emitting its build artifacts directly into
the Django static file hierarchy under a unique subdirectory such
as ``static/react/@smarter/terminal-emulator/``.

.. image:: https://cdn.smarter.sh/docs/smarter-framework/react-integration/react-npm-workspace.png
  :alt: View, Template, and React Component Integration
  :width: 100%

From Django’s perspective, compiled React assets are ultimately treated no
differently than any other static resource such as CSS, images, or JavaScript
files. This architectural decision is intentional and is central to Smarter’s
integration strategy. By ensuring that React build artifacts are emitted directly
into Django’s static file hierarchy before the collectstatic process runs,
the React build pipeline can remain cleanly decoupled from the Django application
runtime itself.

This separation provides several operational advantages. React applications can
be developed, versioned, and rebuilt independently while still integrating
seamlessly into Django’s deployment pipeline. At runtime, Django remains fully
responsible for static asset serving, cache management, CDN integration, and
template rendering, while React remains focused exclusively on frontend behavior
and presentation logic.

There are several important operational considerations related to the build,
deployment, and CI/CD lifecycle of React applications within the Smarter platform:

* Source Control Exclusion
    Compiled React build artifacts are intentionally
    excluded from the Git repository and are never committed to source control.
    Build outputs are considered ephemeral deployment artifacts and must therefore
    be regenerated as part of the build process.
* Build Prerequisites
    Because Django templates and template tags depend
    on the existence of manifest.json and its associated static assets, the
    React build process must execute successfully at least once before the Django
    application can correctly render React-integrated pages. Keep this in mind
    when for example, you are tinkering with versions in package.json.
* CI/CD Pipeline Initialization
    GitHub Actions workflows begin with a clean
    repository checkout that does not contain compiled frontend assets. Accordingly,
    React build steps must run early in the workflow before Docker builds,
    collectstatic, integration tests, or deployment stages that depend on
    these assets.

    .. image:: https://cdn.smarter.sh/docs/smarter-framework/react-integration/gha-build-workflow-for-react.png
       :alt: View, Template, and React Component Integration
       :width: 100%

* Static File Synchronization
    During local development, developers should remain aware of the distinction
    between Vite’s live development server, Django’s static asset directories,
    and the Django staticfiles runtime directory. Stale build artifacts can
    occasionally lead to confusing runtime behavior if these environments become
    out of sync.
* Container Build Dependencies
    Docker images intended to serve React-enabled
    Django pages must be built only after the frontend asset pipeline has completed.
    This ensures that all compiled React bundles and manifest metadata are available
    inside the container image at runtime.
* Convenience Tooling
    Smarter provides helper commands such as `make react-build` and `make react-build-ci`
    to simplify common frontend integration workflows and to keep Django’s
    static directories aligned with current React build outputs.

Collectively, these conventions provide a predictable and highly reproducible
deployment model that works consistently across local development environments,
CI/CD workflows, Docker container builds, and production infrastructure. The
result is a React integration architecture that preserves the operational
simplicity of Django deployments while still enabling modern frontend build
pipelines and advanced React development workflows.

.. toctree::
  :maxdepth: 1
  :caption: Technical Reference

  react-integration/dashboard
  react-integration/prompt-list
  react-integration/terminal-application
  react-integration/prompt-passthrough
  react-integration/smarter-chat
  lib/django/templatetags

.. toctree::
  :maxdepth: 1
  :caption: Code Samples

  react-integration/example-vite
  react-integration/example-template-tag
  react-integration/example-template
  react-integration/example-view
  react-integration/example-react-mount

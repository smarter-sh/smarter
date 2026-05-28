React Integration
=================

The most important parts of the Smarter web console are implemented with React.
We've put considerable thought into how to go about integrating React into a
Django template-based web application, and we've developed a comprehensive strategy
to do so. But before we dive into the details of the strategy, let's take a look
at an example React component mounting in Smarter to get a concrete sense of how
the pieces fit together.

An Example: The Web Console Dashboard
--------------------------------------

Four elements work in concert to bring React-based functionality into the Smarter
web console.


Django Template
~~~~~~~~~~~~~~~~~~~

The Django template is primarily responsible for providing a DOM entry point for the React
component to mount to. It is secondarily responsible for mapping Django view context to
data attributes on the DOM element that serves as the mounting point for the React component.
This context information typically includes salient cookie names for Django session management,
CSRF protection, and so on, as well as any other props vis a vis API end points that the
React component needs in order to function.

.. code-block:: html

  <div
    id="smarter-dashboard-root"
    smarter-cookie-domain="localhost"
    smarter-csrf-cookie-name="csrftoken"
    smarter-django-session-cookie-name="sessionid"
    smarter-my-resources-api-url="/dashboard/api/my-resources/"
    smarter-service-health-api-url="/dashboard/api/service-health/"
  >

Django View
~~~~~~~~~~~~~

The Django view is responsible for mapping the URL end point to the Django html template,
and for generating and passing the view context to the template. This is to say that the
Django view is deliberately simple.

A live example of a Django view that serves the dashboard template:

.. code-block:: python

  class DashboardView(SmarterAuthenticatedNeverCachedWebView):

      template_path = "react/dashboard.html"

      def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:

          context = {
              "react_dashboard": {
                  "root_id": "smarter-dashboard-root",
                  "csrf_cookie_name": settings.CSRF_COOKIE_NAME,
                  "django_session_cookie_name": settings.SESSION_COOKIE_NAME,
                  "cookie_domain": settings.SESSION_COOKIE_DOMAIN,
                  "my_resources_api_url": /path/to/my/resources/api/,
                  "service_health_api_url": /path/to/service/health/api/,
              }
          }
          self.template_path = "react/dashboard.html"

          return render(request, self.template_path, context=context)


Vite Configuration
~~~~~~~~~~~~~~~~~~~~

ViteJS is a powerful and flexible build tool that Smarter user for its React
components. With Vite, Smarter is able to resolve complicated development and
build issues that arise when integrating React into a Django template-based web.
Examples:

- Mapping proxy URLS for API calls in development so that API calls to to Django
  instead of React's development server.
- Building directly into Django's static files directory to eliminate CORS, CSRF,
  and session management issues in development as well as production.
- Generating a manifest.json file with hashed filenames that provides a single
  source of truth for the names and locations of all build assets.
- Optionally pushing built assets to a public read-only AWS CloudFront distribution,
  allowing the options of hosting built assets from a CDN.
- Pruning out console.debug() calls in production builds to avoid leaking
  potentially sensitive information in production.
- Enabling hot module replacement in development for a smooth and efficient
  React development experience.

Here's a live example of Smarter's Vite configuration for the React-based web console dashboard component.

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
    esbuild: {
      pure: ["console.debug"],
    },
    base: command === "serve" ? "/" : `/static/react/${packageName}/`,
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
    build: {
      minify: "esbuild" as const,
      manifest: "manifest.json",
      outDir: `../../smarter/static/react/${packageName}`,
      emptyOutDir: true,
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
    server: {
      proxy: {
        "/workbench/api/listview": "http://localhost:9357",
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
        [`/static/react/${packageName}/`]: {
          target: "http://localhost:5173",
          changeOrigin: true,
          rewrite: (path: string) => path.replace(new RegExp(`^/static/react/${packageName}/`), "/"),
        },
      },
    },
  }));


Django Template Tags
~~~~~~~~~~~~~~~~~~~~~~

Django html templates work hand-in-glove with custom Django template tags that
Smarter has developed to parse the manifest.json file generated by Vite and
generate the appropriate HTML tags for adding the built React component in a
Django template.

.. code-block:: jinja

  {% block style_extra %}
    {{ block.super }}

    {% dashboard_vite_assets "index.html" as assets %}
    {% for css_file in assets.css %}
      <link class="smarter" rel="stylesheet" href="{% static 'react/dashboard/' %}{{ css_file }}">
    {% endfor %}
  {% endblock %}

.. code-block:: jinja

  {% block javascript_extra %}
    {{ block.super }}

    {% dashboard_vite_assets "index.html" as assets %}
    <script class="smarter" type="module" src="{% static 'react/dashboard/' %}{{ assets.js }}"></script>
  {% endblock %}

See this [Django Template Tag](../../../smarter/smarter/apps/dashboard/templatetags/vite_dashboard.py) for Smarter's Django template tags.

Integration Strategy
--------------------

Smarter implements a robust strategy for integrating React components into Django
template-based web pages. At a high level, the strategy involves:

1. **Vite**: Smarter uses Vite.js to build and bundle React components,
   emphasizing simplicity. That is, Smarter has a strong bias towards using Vite's
   defaults. Smarter's Vite configuration works for all of a.) React development,
   b.) Django development, and c.) production builds. No configuration changes are
   needed. Key aspects of the Vite configuration include:

    - *Single Entry Point*: Smarter has a single entry point for all React
      components.
    - *Locally-hosted Builds*: Smarter builds directly into Django's static files
      directory, resulting in fewer moving parts in the build process. Built
      assets are served from Django's static files in both development
      as well as production. Importantly, this fully eliminates any added
      complexity due to CORS, CSRF, and Django session management.
    - *manifest.json*: Vite generates a manifest.json file that provides
      a single source of truth for the names and locations of all build assets.
      Note that Vite's default build logic leads to an indetermined number of
      css output files, making the manifest.json file essential for clean and
      thorough builds.
    - *Development Server*: Smarter supports both Vite's development server for React
      development, which provides hot module replacement and other conveniences, and also
      Django's development server for Django development. Smarter's Vite configuration
      works seamlessly in both contexts without any configuration changes.
    - *Production Builds*: Smarter's Vite configuration also works seamlessly
      for production builds, because build assets are persisted to Django's static
      files directory and the manifest.json file is used to reference the correct
      asset names and locations in production as well.
    - *AWS CloudFront*: Smarter's Vite configuration can optionally push built assets to
      a public read-only AWS CloudFront distribution, allowing the options of
      hosting built assets from a CDN as well as streamlining the Docker
      build process by eliminating the need to use React build tools inside
      of the Docker build process.
2. **Django Template Tags**: Smarter uses custom Django template tags to parse the
   manifest.json file and generate the appropriate HTML tags for adding the
   built React component in a Django templates.
3. **Component Props**: Smarter passes props from Django to React components via
   Django view context, mapped to data attributes on the HTML elements that
   serve as mounting points for the React components. As a matter of practice
   and consistency, the view always passes all salient cookie names for Django
   session management, CSRF protection, etcetera.
4. **Django Templates**: These are deliberately simple and typically limited to
   nothing more than the mounting points for the React components along with the
   attributes mapping the view context to individual data attributes.

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

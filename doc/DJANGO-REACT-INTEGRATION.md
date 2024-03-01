# Django-React Integration

There are several considerations for getting React to work inside a Django project. React's native build tools assume that you're building a standalone web app as opposed to more of a drop-in page component in our case. Additionally, Django does opinionated things with your project's static assets like for example, the css/js bundles that React's build tools create.

## React App Setup

- **placement within folder structure.** The React app was scaffolded with ViteJS and is added to the Django app [chatapp](./smarter/smarter/apps/chatapp/reactapp/).
- **vite.config.ts.** Note that a.) Django's collectstatic procedure must be able to discover the existence of React builds, and that b.) The url scheme in the React-generated templates need to account for how Django serves static assets in both dev and production environments. We leverage the [vite.config.ts](../smarter/smarter/apps/chatapp/reactapp/vite.config.ts) resource to prefix all paths with whatever path we've decided in Django settings for serving static assets. More on this, and a code sample, below.

  ````javascript
  export default defineConfig({
    plugins: [react()],
    base: "/static/",
    build: {
      sourcemap: true,
    },
  });```

  ````

- **index.html.** The original [index.html](./smarter/smarter/apps/chatapp/reactapp/index.html) created by Vite is completely replaced by a django template that a.) inherits our custom smarter/base.html template, b.) contains Django template blocks to ensure correct placement of React's elements within the DOM. More on this, and a code sample, below.

  ```django
  {% extends "smarter/base.html" %}

  {% block content %}
  {% endblock %}

  {% block react_content %}
    {{ block.super }}
    <div id="root"></div>
  {% endblock %}

  {% block react_javascript %}
    {{ block.super }}
    {{ react_config|json_script:'react-config' }}
  {% endblock %}
  ```

## Django Template Engine Configuration

The Django template engine needs to know how to find React-rendered html templates. Note that React's builds are generated in a subfolder named `dist` located in the root folder of the React project, and that it's `index.html` entry point file contains links to auto-generated css and js bundles, meaning that the rendered index.html is specific to the resources in the build that generated it, and it therefore cannot be generalized/templated. Thus, we need a way to gracefully enable Django's templating engine to 'discover' these apps in whichever Django apps they might exist, so that these files can be served by Django templates as-is. To this end we've created a custom React [template loader](./smarter/smarter/template_loader.py) and a 2nd template engine located in [base.py](./smarter/smarter/settings/base.py) that references the custom loader. We additionally created this custom [base template](./smarter/smarter/templates//smarter/base_react.html) for React that ensures that React's `<div id="root"></div>` DOM element and it's js entry point bundle are correctly placed with the DOM.

```python
class ReactAppLoader(FilesystemLoader):
    """A custom template loader that includes each django app's reactapp/dist directory in the search path."""

    def get_dirs(self):

        # checks every Django app for a subfolder named 'reactapp/dist/'
        dirs = super().get_dirs()
        for app in apps.get_app_configs():
            dirs.append(os.path.join(app.path, "reactapp", "dist"))
        return dirs
```

```python
  {
      # our custom template engined is named 'react'
      "NAME": "react",
      "BACKEND": "django.template.backends.django.DjangoTemplates",
      # it must be explicitly instructed to check the project
      # template folder
      "DIRS": [
          BASE_DIR / "templates",
      ],
      "APP_DIRS": False,
      "OPTIONS": {
          "loaders": [
              # our custom template loader goes here...
              "smarter.template_loader.ReactAppLoader",
              "django.template.loaders.filesystem.Loader",
          ],
          "context_processors": [
              # our custom context processor goes here...
              "smarter.apps.dashboard.context_processors.react",
              "django.template.context_processors.request",
              #
              # other context processors ...
              #
          ],
      },
  },
```

### React index.html template

The original `index.html` created by Vite is replaced with this Django template. Note that this template is first processed by React's build process, which will convert the `main.jsx` reference to an actual js bundle filename. And then afterwards, Django's collectstatic procedure will copy the `dist` folder contents to the staticfiles folder, to be served by Django's static asset server.

smarter/base_react.html:

```django
{% extends "smarter/base.html" %}

{% block content %}
{% endblock %}

{% block react_content %}
  {{ block.super }}
  <div id="root"></div>
{% endblock %}

{% block react_javascript %}
  {{ block.super }}
  {{ react_config|json_script:'react-config' }}
{% endblock %}
```

Example Django view template for serving a React app:

```django
{% extends "smarter/base_react.html" %}

{% block canonical %}
<link rel="canonical" href="/chatapp/" />
{% endblock %}

{% block react_javascript %}
  {{ block.super }}
  <script type="module" src="/src/main.jsx"></script>
{% endblock %}
```

### Django TEMPLATES settings

We created this second template engine that is customized for React.

```python
  {
      "NAME": "react",
      "BACKEND": "django.template.backends.django.DjangoTemplates",
      "DIRS": [
          BASE_DIR / "templates",
      ],
      "APP_DIRS": False,
      "OPTIONS": {
          "loaders": [
              "smarter.template_loader.ReactAppLoader",
              "django.template.loaders.filesystem.Loader",
          ],
          "context_processors": [
              "smarter.apps.dashboard.context_processors.react",
              "django.template.context_processors.request",
              #
              # other context processors ...
              #
          ],
      },
  },
```

## Django Static Asset Collection & Serving

### vite.config.ts

Vite is highly configurable, and it greatly simplifies systematically making the kinds of minor adjustments needed to get the React app working inside a Django-managed web page. Note the addition of the `/static/` prefix to all urls that vite generates which, conveniently, are limited to static assets like images, css, and js.

```javascript
export default defineConfig({
  plugins: [react()],
  base: "/static/",
  build: {
    sourcemap: true,
  },
});
```

## Backend integration via template context

The React app interacts with the backend via a REST API implemented with Django REST Framework. But we have to provide the app with the correct, environment-specific url for this API during app startup, along with other similar stateful data. We therefore need a way to pass a small set of data to React via the Django template which invokes it. We created a custom [Django template context](./smarter/smarter/apps/dashboard/context_processors.py) that generates this data, and a [Django base template](./smarter/smarter/templates/smarter/base_react.html) that converts it into a javascript element placed in the DOM, which is then [consumed by the React app](./smarter/smarter/apps/chatapp/reactapp/src/config.js) at startup as a const. Note that the custom React context processor is added to the custom React template engine, described above.

**IMPORTANT:** this integration strategy publicly exposes the data it passes to React. It's not visible to the naked eye mind you, but nonetheless, the data is parked inside the DOM and could be seen by simply perusing the web page's source code view.

### Django context generation

```python
def react(request):
  """
  React context processor for all templates that render
  a React app.
  """

  # https://platform.smarter.sh/
  # http://127.0.0.1:8000/
  base_url = f"{request.scheme}://{request.get_host}"
  return {
      "react": True,
      "react_config": {"BASE_URL": base_url, "API_URL": f"{base_url}/api/v0", "CHAT_ID": "SET-ME-PLEASE"},
  }
```

### Django template setup

The Django base_react.html template includes this snippet which will correctly place React's js bundle near the bottom of the `<body>` of the DOM.

```django
{% block react_javascript %}
  {{ block.super }}
  {{ react_config|json_script:'react-config' }}
{% endblock %}
```

in turn, the template will render a DOM element like the following. Thus, **BE AWARE** that this data is exposed.

```html
<script id="react-config" type="application/json">
  {
    "BASE_URL": "http://127.0.0.1:8000",
    "API_URL": "http://127.0.0.1:8000/api/v0",
    "CHAT_ID": "SET-ME-PLEASE"
  }
</script>
```

### React app consumption

The DOM element can be consumed by JS/React like this:

```javascript
export const REACT_CONFIG = JSON.parse(
  document.getElementById("react-config").textContent,
);
```

## CORS Configuration

In dev we have to deal with CORS because, for development purposes, React is served from a different port, http://localhost:5173/, than Django is, http://127.0.0.1:8000/.

The following additional settings are necessary for the local dev environment:

```python
INSTALLED_APPS += [
    "corsheaders",
]
MIDDLEWARE += [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
]

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
]

# for any React-based implementations of plugin technologies
# like say, Wordpress, Drupal, salesforce, etc.
CORS_ALLOW_HEADERS = list(default_headers) + [
    "x-api-key",
]
```

## Authentication & CSRF

Web-based session authentication managed by Django, which is nice as it's one less thing we have to worry about in React. However, in doing so we oblige ourselves to additionally working with Django's built-in protections against Cross-Site Request Forgery (CSRF), which is cookie-based. Django's default name for the cookie it creates is, "csrftoken".

```javascript
const csrftoken = getCookie("csrftoken");
const headers = {
  Accept: "*/*",
  "Content-Type": "application/json",
  "X-CSRFToken": csrftoken, // <---- add this to all request headers
  Origin: window.location.origin,
};
```
